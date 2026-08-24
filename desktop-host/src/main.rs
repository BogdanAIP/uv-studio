#![windows_subsystem = "windows"]

use std::{cell::RefCell, env, ptr, sync::mpsc};

use webview2_com::{
    Microsoft::Web::WebView2::Win32::*,
    CoTaskMemPWSTR,
    CreateCoreWebView2ControllerCompletedHandler,
    CreateCoreWebView2EnvironmentCompletedHandler,
    NavigationCompletedEventHandler,
    NavigationStartingEventHandler,
    NewWindowRequestedEventHandler,
};
use windows::{
    core::{w, Error as WindowsError, PCWSTR, PWSTR},
    Win32::{
        Foundation::{E_POINTER, HINSTANCE, HWND, LPARAM, LRESULT, RECT, WPARAM},
        System::{
            Com::{CoInitializeEx, CoUninitialize, COINIT_APARTMENTTHREADED},
            LibraryLoader::GetModuleHandleW,
        },
        UI::{
            HiDpi::{SetProcessDpiAwareness, PROCESS_PER_MONITOR_DPI_AWARE},
            Shell::ShellExecuteW,
            WindowsAndMessaging::{
                CreateWindowExW, DefWindowProcW, DestroyWindow, DispatchMessageW, GetClientRect,
                GetMessageW, LoadCursorW, PostQuitMessage, RegisterClassW, ShowWindow,
                TranslateMessage, CREATESTRUCTW, CW_USEDEFAULT, IDC_ARROW, MINMAXINFO, MSG,
                SW_HIDE, SW_SHOW, SW_SHOWNORMAL, WINDOW_EX_STYLE, WM_CLOSE, WM_DESTROY,
                WM_GETMINMAXINFO, WM_SIZE, WNDCLASSW, WS_OVERLAPPEDWINDOW,
            },
        },
    },
};

const LOCAL_ORIGIN: &str = "http://127.0.0.1:3000";
const WINDOW_CLASS: windows::core::PCWSTR = w!("UVStudioDesktopHost");
const WINDOW_TITLE: windows::core::PCWSTR = w!("UV Studio");

thread_local! {
    static CONTROLLER: RefCell<Option<ICoreWebView2Controller>> = const { RefCell::new(None) };
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct Options {
    url: String,
    smoke: bool,
    runtime_check: bool,
}

fn parse_arguments<I>(arguments: I) -> Result<Options, String>
where
    I: IntoIterator<Item = String>,
{
    let mut args = arguments.into_iter();
    let _program = args.next();
    let mut url = LOCAL_ORIGIN.to_owned();
    let mut smoke = false;
    let mut runtime_check = false;

    while let Some(argument) = args.next() {
        match argument.as_str() {
            "--url" => {
                url = args
                    .next()
                    .ok_or_else(|| "--url requires a value".to_owned())?;
            }
            "--smoke" => smoke = true,
            "--runtime-check" => runtime_check = true,
            _ => return Err(format!("unsupported argument: {argument}")),
        }
    }

    if !is_local_url(&url) {
        return Err("desktop URL must stay inside the packaged loopback frontend".to_owned());
    }
    if runtime_check && smoke {
        return Err("--runtime-check and --smoke are mutually exclusive".to_owned());
    }

    Ok(Options {
        url,
        smoke,
        runtime_check,
    })
}

fn is_local_url(url: &str) -> bool {
    url == LOCAL_ORIGIN
        || url
            .strip_prefix(LOCAL_ORIGIN)
            .is_some_and(|rest| rest.starts_with('/') || rest.starts_with('?') || rest.starts_with('#'))
}

fn is_allowed_external_url(url: &str) -> bool {
    let normalized = url.to_ascii_lowercase();
    normalized.starts_with("https://") || normalized.starts_with("http://")
}

fn webview2_runtime_available() -> bool {
    let mut version = PWSTR::null();
    let result = unsafe { GetAvailableCoreWebView2BrowserVersionString(PCWSTR::null(), &mut version) };
    if !version.is_null() {
        drop(CoTaskMemPWSTR::from(version));
    }
    result.is_ok()
}

fn show_error(message: &str) {
    let text = CoTaskMemPWSTR::from(message);
    unsafe {
        let _ = windows::Win32::UI::WindowsAndMessaging::MessageBoxW(
            None,
            *text.as_ref().as_pcwstr(),
            WINDOW_TITLE,
            windows::Win32::UI::WindowsAndMessaging::MB_OK
                | windows::Win32::UI::WindowsAndMessaging::MB_ICONERROR,
        );
    }
}

fn open_external(uri: &str) {
    if !is_allowed_external_url(uri) {
        return;
    }
    let target = CoTaskMemPWSTR::from(uri);
    unsafe {
        let _ = ShellExecuteW(
            None,
            w!("open"),
            *target.as_ref().as_pcwstr(),
            PCWSTR::null(),
            PCWSTR::null(),
            SW_SHOWNORMAL,
        );
    }
}

fn window_client_rect(hwnd: HWND) -> RECT {
    let mut bounds = RECT::default();
    unsafe {
        let _ = GetClientRect(hwnd, &mut bounds);
    }
    bounds
}

fn resize_controller(hwnd: HWND) {
    let bounds = window_client_rect(hwnd);
    CONTROLLER.with(|slot| {
        if let Some(controller) = slot.borrow().as_ref() {
            unsafe {
                let _ = controller.SetBounds(bounds);
            }
        }
    });
}

extern "system" fn window_proc(hwnd: HWND, message: u32, w_param: WPARAM, l_param: LPARAM) -> LRESULT {
    match message {
        WM_SIZE => {
            resize_controller(hwnd);
            LRESULT(0)
        }
        WM_GETMINMAXINFO => {
            let info = l_param.0 as *mut MINMAXINFO;
            if !info.is_null() {
                unsafe {
                    (*info).ptMinTrackSize.x = 960;
                    (*info).ptMinTrackSize.y = 640;
                }
            }
            LRESULT(0)
        }
        WM_CLOSE => {
            unsafe {
                let _ = DestroyWindow(hwnd);
            }
            LRESULT(0)
        }
        WM_DESTROY => {
            CONTROLLER.with(|slot| {
                if let Some(controller) = slot.borrow_mut().take() {
                    unsafe {
                        let _ = controller.Close();
                    }
                }
            });
            unsafe { PostQuitMessage(0) };
            LRESULT(0)
        }
        _ => unsafe { DefWindowProcW(hwnd, message, w_param, l_param) },
    }
}

fn create_window(smoke: bool) -> Result<HWND, WindowsError> {
    let module = unsafe { GetModuleHandleW(None)? };
    let instance = HINSTANCE(module.0);
    let window_class = WNDCLASSW {
        lpfnWndProc: Some(window_proc),
        hInstance: instance,
        lpszClassName: WINDOW_CLASS,
        hCursor: unsafe { LoadCursorW(None, IDC_ARROW)? },
        ..Default::default()
    };

    unsafe {
        RegisterClassW(&window_class);
    }

    let hwnd = unsafe {
        CreateWindowExW(
            WINDOW_EX_STYLE::default(),
            WINDOW_CLASS,
            WINDOW_TITLE,
            WS_OVERLAPPEDWINDOW,
            CW_USEDEFAULT,
            CW_USEDEFAULT,
            1440,
            900,
            None,
            None,
            Some(instance),
            None,
        )?
    };

    unsafe {
        let _ = ShowWindow(hwnd, if smoke { SW_HIDE } else { SW_SHOW });
    }
    Ok(hwnd)
}

fn create_environment() -> Result<ICoreWebView2Environment, webview2_com::Error> {
    let (tx, rx) = mpsc::channel();
    CreateCoreWebView2EnvironmentCompletedHandler::wait_for_async_operation(
        Box::new(|handler| unsafe {
            CreateCoreWebView2Environment(&handler).map_err(webview2_com::Error::WindowsError)
        }),
        Box::new(move |result, environment| {
            result?;
            tx.send(environment.ok_or_else(|| WindowsError::from(E_POINTER)))
                .map_err(|_| WindowsError::from(E_POINTER))?;
            Ok(())
        }),
    )?;
    webview2_com::wait_with_pump(rx)?.map_err(webview2_com::Error::WindowsError)
}

fn create_controller(
    environment: &ICoreWebView2Environment,
    hwnd: HWND,
) -> Result<ICoreWebView2Controller, webview2_com::Error> {
    let environment = environment.clone();
    let (tx, rx) = mpsc::channel();
    CreateCoreWebView2ControllerCompletedHandler::wait_for_async_operation(
        Box::new(move |handler| unsafe {
            environment
                .CreateCoreWebView2Controller(hwnd, &handler)
                .map_err(webview2_com::Error::WindowsError)
        }),
        Box::new(move |result, controller| {
            result?;
            tx.send(controller.ok_or_else(|| WindowsError::from(E_POINTER)))
                .map_err(|_| WindowsError::from(E_POINTER))?;
            Ok(())
        }),
    )?;
    webview2_com::wait_with_pump(rx)?.map_err(webview2_com::Error::WindowsError)
}

fn configure_webview(
    hwnd: HWND,
    controller: &ICoreWebView2Controller,
    webview: &ICoreWebView2,
) -> Result<(), webview2_com::Error> {
    unsafe {
        controller
            .SetBounds(window_client_rect(hwnd))
            .map_err(webview2_com::Error::WindowsError)?;
        controller
            .SetIsVisible(true)
            .map_err(webview2_com::Error::WindowsError)?;

        let settings = webview
            .Settings()
            .map_err(webview2_com::Error::WindowsError)?;
        settings
            .SetAreDefaultContextMenusEnabled(false)
            .map_err(webview2_com::Error::WindowsError)?;
        settings
            .SetAreDevToolsEnabled(false)
            .map_err(webview2_com::Error::WindowsError)?;
        settings
            .SetIsStatusBarEnabled(false)
            .map_err(webview2_com::Error::WindowsError)?;
    }

    let navigation_handler = NavigationStartingEventHandler::create(Box::new(move |_sender, args| {
        if let Some(args) = args {
            let mut raw = PWSTR::null();
            unsafe {
                args.Uri(&mut raw)?;
            }
            let uri = CoTaskMemPWSTR::from(raw).to_string();
            if !is_local_url(&uri) {
                unsafe {
                    args.SetCancel(true)?;
                }
                open_external(&uri);
            }
        }
        Ok(())
    }));
    let mut navigation_token = 0;
    unsafe {
        webview
            .add_NavigationStarting(&navigation_handler, &mut navigation_token)
            .map_err(webview2_com::Error::WindowsError)?;
    }

    let new_window_handler = NewWindowRequestedEventHandler::create(Box::new(move |sender, args| {
        if let Some(args) = args {
            let mut raw = PWSTR::null();
            unsafe {
                args.Uri(&mut raw)?;
            }
            let uri = CoTaskMemPWSTR::from(raw).to_string();
            unsafe {
                args.SetHandled(true)?;
            }
            if is_local_url(&uri) {
                if let Some(sender) = sender {
                    let target = CoTaskMemPWSTR::from(uri.as_str());
                    unsafe {
                        sender.Navigate(*target.as_ref().as_pcwstr())?;
                    }
                }
            } else {
                open_external(&uri);
            }
        }
        Ok(())
    }));
    let mut new_window_token = 0;
    unsafe {
        webview
            .add_NewWindowRequested(&new_window_handler, &mut new_window_token)
            .map_err(webview2_com::Error::WindowsError)?;
    }

    Ok(())
}

fn navigate_and_wait(webview: &ICoreWebView2, url: &str) -> Result<(), webview2_com::Error> {
    let (tx, rx) = mpsc::channel();
    let handler = NavigationCompletedEventHandler::create(Box::new(move |_sender, args| {
        let success = if let Some(args) = args {
            let mut success = windows::core::BOOL::from(false);
            unsafe {
                args.IsSuccess(&mut success)?;
            }
            success.as_bool()
        } else {
            false
        };
        let _ = tx.send(success);
        Ok(())
    }));
    let mut token = 0;
    unsafe {
        webview
            .add_NavigationCompleted(&handler, &mut token)
            .map_err(webview2_com::Error::WindowsError)?;
        let target = CoTaskMemPWSTR::from(url);
        webview
            .Navigate(*target.as_ref().as_pcwstr())
            .map_err(webview2_com::Error::WindowsError)?;
    }
    let success = webview2_com::wait_with_pump(rx)?;
    unsafe {
        webview
            .remove_NavigationCompleted(token)
            .map_err(webview2_com::Error::WindowsError)?;
    }
    if success {
        Ok(())
    } else {
        Err(webview2_com::Error::CallbackError(
            "packaged frontend navigation failed".to_owned(),
        ))
    }
}

fn run(options: Options) -> Result<i32, String> {
    if options.runtime_check {
        return Ok(if webview2_runtime_available() { 0 } else { 2 });
    }
    if !webview2_runtime_available() {
        if !options.smoke {
            show_error(
                "Для запуска UV Studio требуется Microsoft Edge WebView2 Runtime. Обновите Microsoft Edge или установите WebView2 Runtime и запустите UV Studio снова.",
            );
        }
        return Ok(2);
    }

    unsafe {
        CoInitializeEx(None, COINIT_APARTMENTTHREADED)
            .ok()
            .map_err(|error| format!("COM initialization failed: {error}"))?;
    }
    let _com_guard = ComGuard;

    unsafe {
        SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)
            .map_err(|error| format!("DPI initialization failed: {error}"))?;
    }

    let hwnd = create_window(options.smoke).map_err(|error| format!("window creation failed: {error}"))?;
    let environment = create_environment().map_err(|error| format!("WebView2 environment failed: {error}"))?;
    let controller = create_controller(&environment, hwnd)
        .map_err(|error| format!("WebView2 controller failed: {error}"))?;
    let webview = unsafe { controller.CoreWebView2() }
        .map_err(|error| format!("WebView2 instance failed: {error}"))?;
    configure_webview(hwnd, &controller, &webview)
        .map_err(|error| format!("WebView2 configuration failed: {error}"))?;
    CONTROLLER.with(|slot| *slot.borrow_mut() = Some(controller));

    navigate_and_wait(&webview, &options.url)
        .map_err(|error| format!("UV Studio navigation failed: {error}"))?;

    if options.smoke {
        unsafe {
            let _ = DestroyWindow(hwnd);
        }
        return Ok(0);
    }

    let mut message = MSG::default();
    loop {
        let state = unsafe { GetMessageW(&mut message, None, 0, 0).0 };
        match state {
            -1 => return Err("Windows message loop failed".to_owned()),
            0 => return Ok(message.wParam.0 as i32),
            _ => unsafe {
                let _ = TranslateMessage(&message);
                DispatchMessageW(&message);
            },
        }
    }
}

struct ComGuard;

impl Drop for ComGuard {
    fn drop(&mut self) {
        unsafe { CoUninitialize() };
    }
}

fn main() {
    let options = match parse_arguments(env::args()) {
        Ok(options) => options,
        Err(_) => std::process::exit(2),
    };

    match run(options.clone()) {
        Ok(code) => std::process::exit(code),
        Err(_) => {
            if !options.smoke && !options.runtime_check {
                show_error(
                    "UV Studio не смог открыть встроенное окно. Закройте программу и запустите её снова. Если ошибка повторится, откройте раздел диагностики после следующего успешного запуска.",
                );
            }
            std::process::exit(2);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn args(values: &[&str]) -> Vec<String> {
        values.iter().map(|value| (*value).to_owned()).collect()
    }

    #[test]
    fn accepts_only_packaged_loopback_origin() {
        for accepted in [
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3000/",
            "http://127.0.0.1:3000/projects/demo",
            "http://127.0.0.1:3000?mode=desktop",
            "http://127.0.0.1:3000#timeline",
        ] {
            assert!(is_local_url(accepted), "expected local URL: {accepted}");
        }
        for rejected in [
            "https://127.0.0.1:3000/",
            "http://localhost:3000/",
            "http://127.0.0.1:3000.evil/",
            "http://127.0.0.1:30000/",
            "https://example.com/",
        ] {
            assert!(!is_local_url(rejected), "expected rejection: {rejected}");
        }
    }

    #[test]
    fn allows_only_web_schemes_for_external_navigation() {
        for accepted in [
            "https://example.com/",
            "http://example.com/path",
            "HTTPS://EXAMPLE.COM/",
        ] {
            assert!(is_allowed_external_url(accepted), "expected external URL: {accepted}");
        }
        for rejected in [
            "file:///C:/Windows/System32/calc.exe",
            "javascript:alert(1)",
            "ms-settings:privacy",
            "mailto:user@example.com",
            "httpsx://example.com/",
        ] {
            assert!(!is_allowed_external_url(rejected), "expected external URL rejection: {rejected}");
        }
    }

    #[test]
    fn parses_smoke_and_url_without_extra_surface() {
        let parsed = parse_arguments(args(&[
            "uv-studio-desktop.exe",
            "--url",
            "http://127.0.0.1:3000/projects/demo",
            "--smoke",
        ]))
        .unwrap();
        assert!(parsed.smoke);
        assert!(!parsed.runtime_check);
        assert_eq!(parsed.url, "http://127.0.0.1:3000/projects/demo");
    }

    #[test]
    fn rejects_unknown_or_conflicting_arguments() {
        assert!(parse_arguments(args(&["uv-studio-desktop.exe", "--browser"])).is_err());
        assert!(parse_arguments(args(&[
            "uv-studio-desktop.exe",
            "--runtime-check",
            "--smoke",
        ]))
        .is_err());
    }
}
