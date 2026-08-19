#include <windows.h>
#include <shellapi.h>
#include <wrl.h>
#include <string>
#include "WebView2.h"

using Microsoft::WRL::Callback;
using Microsoft::WRL::ComPtr;

namespace {
constexpr wchar_t kWindowClass[] = L"UVStudioDesktopHost";
constexpr wchar_t kWindowTitle[] = L"UV Studio";
constexpr wchar_t kLocalOrigin[] = L"http://127.0.0.1:3000";

HWND g_window = nullptr;
ComPtr<ICoreWebView2Controller> g_controller;
ComPtr<ICoreWebView2> g_webview;
std::wstring g_start_url = kLocalOrigin;
std::wstring g_user_data_dir;

bool StartsWith(const std::wstring& value, const std::wstring& prefix) {
    return value.size() >= prefix.size() && value.compare(0, prefix.size(), prefix) == 0;
}

bool IsLocalNavigation(const std::wstring& uri) {
    const std::wstring origin = kLocalOrigin;
    return uri == origin || StartsWith(uri, origin + L"/") || StartsWith(uri, origin + L"?") || StartsWith(uri, origin + L"#");
}

void OpenExternalUri(const std::wstring& uri) {
    if (uri.empty()) return;
    ShellExecuteW(g_window, L"open", uri.c_str(), nullptr, nullptr, SW_SHOWNORMAL);
}

void ShowFatal(const wchar_t* message) {
    MessageBoxW(g_window, message, kWindowTitle, MB_OK | MB_ICONERROR);
    if (g_window) {
        PostMessageW(g_window, WM_CLOSE, 0, 0);
    }
}

std::wstring ReadUri(LPWSTR raw) {
    if (!raw) return {};
    std::wstring value(raw);
    CoTaskMemFree(raw);
    return value;
}

void ResizeWebView() {
    if (!g_controller || !g_window) return;
    RECT bounds{};
    GetClientRect(g_window, &bounds);
    g_controller->put_Bounds(bounds);
}

HRESULT ConfigureWebView(ICoreWebView2* webview) {
    if (!webview) return E_POINTER;
    g_webview = webview;

    ComPtr<ICoreWebView2Settings> settings;
    if (SUCCEEDED(g_webview->get_Settings(&settings)) && settings) {
        settings->put_IsScriptEnabled(TRUE);
        settings->put_AreDefaultScriptDialogsEnabled(TRUE);
        settings->put_IsWebMessageEnabled(TRUE);
        settings->put_AreDefaultContextMenusEnabled(TRUE);
        settings->put_AreDevToolsEnabled(FALSE);
        settings->put_IsStatusBarEnabled(FALSE);
        settings->put_IsZoomControlEnabled(TRUE);
    }

    EventRegistrationToken navigation_token{};
    g_webview->add_NavigationStarting(
        Callback<ICoreWebView2NavigationStartingEventHandler>(
            [](ICoreWebView2*, ICoreWebView2NavigationStartingEventArgs* args) -> HRESULT {
                LPWSTR raw = nullptr;
                if (FAILED(args->get_Uri(&raw))) return S_OK;
                const std::wstring uri = ReadUri(raw);
                if (IsLocalNavigation(uri)) return S_OK;
                args->put_Cancel(TRUE);
                OpenExternalUri(uri);
                return S_OK;
            }).Get(),
        &navigation_token);

    EventRegistrationToken new_window_token{};
    g_webview->add_NewWindowRequested(
        Callback<ICoreWebView2NewWindowRequestedEventHandler>(
            [](ICoreWebView2*, ICoreWebView2NewWindowRequestedEventArgs* args) -> HRESULT {
                LPWSTR raw = nullptr;
                if (FAILED(args->get_Uri(&raw))) return S_OK;
                const std::wstring uri = ReadUri(raw);
                args->put_Handled(TRUE);
                if (IsLocalNavigation(uri)) {
                    if (g_webview) g_webview->Navigate(uri.c_str());
                } else {
                    OpenExternalUri(uri);
                }
                return S_OK;
            }).Get(),
        &new_window_token);

    return g_webview->Navigate(g_start_url.c_str());
}

void InitializeWebView() {
    LPWSTR version = nullptr;
    const HRESULT available = GetAvailableCoreWebView2BrowserVersionString(nullptr, &version);
    if (version) CoTaskMemFree(version);
    if (FAILED(available)) {
        ShowFatal(L"Для запуска UV Studio требуется Microsoft Edge WebView2 Runtime. Обновите Microsoft Edge или установите WebView2 Runtime и запустите UV Studio снова.");
        return;
    }

    const wchar_t* user_data = g_user_data_dir.empty() ? nullptr : g_user_data_dir.c_str();
    const HRESULT created = CreateCoreWebView2EnvironmentWithOptions(
        nullptr,
        user_data,
        nullptr,
        Callback<ICoreWebView2CreateCoreWebView2EnvironmentCompletedHandler>(
            [](HRESULT result, ICoreWebView2Environment* environment) -> HRESULT {
                if (FAILED(result) || !environment) {
                    ShowFatal(L"Не удалось запустить встроенное окно UV Studio (WebView2 environment).");
                    return S_OK;
                }
                return environment->CreateCoreWebView2Controller(
                    g_window,
                    Callback<ICoreWebView2CreateCoreWebView2ControllerCompletedHandler>(
                        [](HRESULT controller_result, ICoreWebView2Controller* controller) -> HRESULT {
                            if (FAILED(controller_result) || !controller) {
                                ShowFatal(L"Не удалось создать встроенное окно UV Studio (WebView2 controller).");
                                return S_OK;
                            }
                            g_controller = controller;
                            ResizeWebView();
                            g_controller->put_IsVisible(TRUE);
                            ComPtr<ICoreWebView2> webview;
                            if (FAILED(g_controller->get_CoreWebView2(&webview)) || !webview) {
                                ShowFatal(L"Не удалось открыть интерфейс UV Studio.");
                                return S_OK;
                            }
                            if (FAILED(ConfigureWebView(webview.Get()))) {
                                ShowFatal(L"Не удалось загрузить интерфейс UV Studio.");
                            }
                            return S_OK;
                        }).Get());
            }).Get());
    if (FAILED(created)) {
        ShowFatal(L"Не удалось инициализировать Microsoft Edge WebView2 Runtime.");
    }
}

LRESULT CALLBACK WindowProc(HWND window, UINT message, WPARAM w_param, LPARAM l_param) {
    switch (message) {
    case WM_SIZE:
        ResizeWebView();
        return 0;
    case WM_DPICHANGED: {
        const RECT* suggested = reinterpret_cast<RECT*>(l_param);
        if (suggested) {
            SetWindowPos(window, nullptr, suggested->left, suggested->top,
                         suggested->right - suggested->left,
                         suggested->bottom - suggested->top,
                         SWP_NOZORDER | SWP_NOACTIVATE);
        }
        return 0;
    }
    case WM_GETMINMAXINFO: {
        auto* info = reinterpret_cast<MINMAXINFO*>(l_param);
        info->ptMinTrackSize.x = 960;
        info->ptMinTrackSize.y = 640;
        return 0;
    }
    case WM_DESTROY:
        if (g_controller) {
            g_controller->Close();
            g_controller.Reset();
            g_webview.Reset();
        }
        PostQuitMessage(0);
        return 0;
    default:
        return DefWindowProcW(window, message, w_param, l_param);
    }
}

bool ParseArguments(int argc, wchar_t** argv, bool& runtime_check) {
    runtime_check = false;
    for (int index = 1; index < argc; ++index) {
        const std::wstring argument = argv[index];
        if (argument == L"--runtime-check") {
            runtime_check = true;
        } else if (argument == L"--url" && index + 1 < argc) {
            g_start_url = argv[++index];
        } else if (argument == L"--user-data-dir" && index + 1 < argc) {
            g_user_data_dir = argv[++index];
        } else {
            return false;
        }
    }
    return true;
}

int RuntimeCheck() {
    LPWSTR version = nullptr;
    const HRESULT result = GetAvailableCoreWebView2BrowserVersionString(nullptr, &version);
    if (version) CoTaskMemFree(version);
    return SUCCEEDED(result) ? 0 : 2;
}
}  // namespace

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE, PWSTR, int show_command) {
    SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);

    int argc = 0;
    LPWSTR* argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (!argv) return 2;
    bool runtime_check = false;
    const bool valid_arguments = ParseArguments(argc, argv, runtime_check);
    LocalFree(argv);
    if (!valid_arguments) return 2;
    if (runtime_check) return RuntimeCheck();
    if (!IsLocalNavigation(g_start_url)) return 2;

    const HRESULT com = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
    if (FAILED(com) && com != RPC_E_CHANGED_MODE) return 2;

    WNDCLASSEXW window_class{};
    window_class.cbSize = sizeof(window_class);
    window_class.style = CS_HREDRAW | CS_VREDRAW;
    window_class.lpfnWndProc = WindowProc;
    window_class.hInstance = instance;
    window_class.hCursor = LoadCursorW(nullptr, IDC_ARROW);
    window_class.hIcon = LoadIconW(nullptr, IDI_APPLICATION);
    window_class.hIconSm = LoadIconW(nullptr, IDI_APPLICATION);
    window_class.hbrBackground = CreateSolidBrush(RGB(16, 18, 21));
    window_class.lpszClassName = kWindowClass;
    if (!RegisterClassExW(&window_class)) {
        CoUninitialize();
        return 2;
    }

    g_window = CreateWindowExW(
        0,
        kWindowClass,
        kWindowTitle,
        WS_OVERLAPPEDWINDOW,
        CW_USEDEFAULT,
        CW_USEDEFAULT,
        1440,
        900,
        nullptr,
        nullptr,
        instance,
        nullptr);
    if (!g_window) {
        CoUninitialize();
        return 2;
    }

    ShowWindow(g_window, show_command == 0 ? SW_SHOWNORMAL : show_command);
    UpdateWindow(g_window);
    InitializeWebView();

    MSG message{};
    while (GetMessageW(&message, nullptr, 0, 0) > 0) {
        TranslateMessage(&message);
        DispatchMessageW(&message);
    }

    CoUninitialize();
    return static_cast<int>(message.wParam);
}
