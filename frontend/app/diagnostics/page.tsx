'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

type Integrity = {
  ok: boolean;
  verify_hashes: boolean;
  checked_files: number;
  problems: string[];
};

type Diagnostics = {
  schema_version: number;
  overall_status: 'ok' | 'degraded' | 'invalid_release' | string;
  mode: 'packaged' | 'development' | string;
  product_version: string;
  runtime: {
    python: string;
    implementation: string;
    os: string;
    architecture: string;
    frozen: boolean;
  };
  resources: {
    logical_cpu_count: number | null;
    memory: {
      total_bytes: number | null;
      available_bytes: number | null;
      source: string;
    };
  };
  release: {
    configured: boolean;
    manifest_valid: boolean | null;
    integrity: Integrity | null;
    product_version: string | null;
    build_id: string | null;
    target: { os: string; arch: string } | null;
    problems: string[];
  };
  media_tools: Record<string, {
    available: boolean;
    source: string;
    release_component: string | null;
  }>;
  storage: {
    probe_performed: boolean;
    user_data: { writable: boolean | null; free_bytes: number | null };
    project_store: { writable: boolean | null; free_bytes: number | null };
    configuration: { writable: boolean | null; free_bytes: number | null };
  };
  recovery: {
    checked: boolean;
    snapshot_count: number | null;
    valid_snapshot_count: number | null;
    invalid_snapshot_count: number | null;
    incomplete_staging_count: number | null;
    latest_created_at: string | null;
  };
  issues: Array<{
    code: string;
    severity: string;
    message: string;
  }>;
};

type CheckKind = 'quick' | 'full';

function formatBytes(value: number | null) {
  if (value === null) return 'не проверено';
  const units = ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ'];
  let amount = value;
  let unit = 0;
  while (amount >= 1024 && unit < units.length - 1) {
    amount /= 1024;
    unit += 1;
  }
  return `${amount.toFixed(unit > 1 ? 1 : 0)} ${units[unit]}`;
}

function formatDate(value: string | null) {
  if (!value) return 'нет';
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString('ru-RU');
}

function statusLabel(status: Diagnostics['overall_status']) {
  if (status === 'ok') return 'Исправно';
  if (status === 'degraded') return 'Есть предупреждения';
  if (status === 'invalid_release') return 'Повреждён выпуск';
  return status;
}

function statusClass(status: Diagnostics['overall_status']) {
  if (status === 'ok') return 'border-emerald-700/60 bg-emerald-950/50 text-emerald-300';
  if (status === 'degraded') return 'border-amber-700/60 bg-amber-950/50 text-amber-300';
  return 'border-rose-700/60 bg-rose-950/50 text-rose-300';
}

function booleanText(value: boolean | null, positive = 'да', negative = 'нет') {
  if (value === null) return 'не проверено';
  return value ? positive : negative;
}

function StorageLine({
  label,
  value,
}: {
  label: string;
  value: { writable: boolean | null; free_bytes: number | null };
}) {
  const state = value.writable === null ? 'не проверено' : value.writable ? 'доступна запись' : 'нет записи';
  return (
    <div className="flex flex-col gap-1 border-b border-slate-800 py-3 last:border-b-0 sm:flex-row sm:items-center sm:justify-between">
      <span className="text-sm text-slate-300">{label}</span>
      <span className={value.writable === false ? 'text-sm text-rose-300' : 'text-sm text-slate-400'}>
        {state}{value.writable ? ` · свободно ${formatBytes(value.free_bytes)}` : ''}
      </span>
    </div>
  );
}

async function fetchDiagnostics(kind: CheckKind): Promise<Diagnostics> {
  const query = kind === 'full' ? '?verify_release=true&probe_storage=true' : '';
  const response = await fetch(`/api/uv/diagnostics${query}`, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Диагностика вернула HTTP ${response.status}`);
  }
  return response.json() as Promise<Diagnostics>;
}

export default function DiagnosticsPage() {
  const [diagnostics, setDiagnostics] = useState<Diagnostics | null>(null);
  const [loading, setLoading] = useState(true);
  const [fullCheckRunning, setFullCheckRunning] = useState(false);
  const [lastCheck, setLastCheck] = useState<CheckKind>('quick');
  const [error, setError] = useState<string | null>(null);

  async function load(kind: CheckKind) {
    if (kind === 'full') setFullCheckRunning(true);
    else setLoading(true);
    setError(null);
    try {
      const result = await fetchDiagnostics(kind);
      setDiagnostics(result);
      setLastCheck(kind);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось выполнить диагностику');
    } finally {
      setLoading(false);
      setFullCheckRunning(false);
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load('quick');
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const integrity = diagnostics?.release.integrity ?? null;
  const media = diagnostics ? Object.entries(diagnostics.media_tools) : [];
  const recovery = diagnostics?.recovery;

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-10 flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="mb-2 text-sm font-medium uppercase tracking-[0.2em] text-sky-400">UV Studio</p>
            <h1 className="text-4xl font-semibold tracking-tight">Диагностика и восстановление</h1>
            <p className="mt-3 max-w-3xl text-slate-400">
              Проверка выпуска, ресурсов компьютера, встроенных медиасредств, пользовательского хранилища и снимков восстановления. Пути, ключи и другие секретные данные здесь не отображаются.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/projects"
              className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-700 px-4 text-sm text-slate-200 transition hover:border-sky-600 hover:bg-slate-900"
            >
              Проекты и архивы
            </Link>
            <button
              type="button"
              onClick={() => void load('full')}
              disabled={fullCheckRunning || loading}
              className="inline-flex h-10 items-center justify-center rounded-lg bg-sky-500 px-4 text-sm font-medium text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {fullCheckRunning ? 'Полная проверка…' : 'Запустить полную проверку'}
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 rounded-xl border border-rose-800 bg-rose-950/50 px-4 py-3 text-sm text-rose-200">
            {error}
          </div>
        )}

        {loading && !diagnostics ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-8 text-slate-400">
            Чтение состояния UV Studio…
          </div>
        ) : diagnostics ? (
          <div className="space-y-6">
            <section className="grid gap-4 md:grid-cols-3">
              <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Общее состояние</p>
                    <p className="mt-2 text-xl font-semibold">UV Studio {diagnostics.product_version}</p>
                  </div>
                  <span className={`rounded-full border px-3 py-1 text-xs font-medium ${statusClass(diagnostics.overall_status)}`}>
                    {statusLabel(diagnostics.overall_status)}
                  </span>
                </div>
                <dl className="mt-5 space-y-2 text-sm">
                  <div className="flex justify-between gap-4"><dt className="text-slate-500">Режим</dt><dd>{diagnostics.mode === 'packaged' ? 'установленный выпуск' : 'разработка'}</dd></div>
                  <div className="flex justify-between gap-4"><dt className="text-slate-500">Python</dt><dd>{diagnostics.runtime.python}</dd></div>
                  <div className="flex justify-between gap-4"><dt className="text-slate-500">Платформа</dt><dd>{diagnostics.runtime.os} · {diagnostics.runtime.architecture}</dd></div>
                </dl>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 md:col-span-2">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Целостность выпуска</p>
                <div className="mt-3 grid gap-3 sm:grid-cols-3">
                  <div className="rounded-xl bg-slate-950/70 p-4">
                    <p className="text-xs text-slate-500">Манифест</p>
                    <p className="mt-1 font-medium">{diagnostics.release.configured ? booleanText(diagnostics.release.manifest_valid, 'валиден', 'ошибка') : 'режим разработки'}</p>
                  </div>
                  <div className="rounded-xl bg-slate-950/70 p-4">
                    <p className="text-xs text-slate-500">Проверка SHA-256</p>
                    <p className="mt-1 font-medium">{integrity?.verify_hashes ? 'выполнена' : 'не запускалась'}</p>
                  </div>
                  <div className="rounded-xl bg-slate-950/70 p-4">
                    <p className="text-xs text-slate-500">Проверено файлов</p>
                    <p className="mt-1 font-medium">{integrity ? integrity.checked_files.toLocaleString('ru-RU') : '—'}</p>
                  </div>
                </div>
                <p className="mt-4 text-sm text-slate-400">
                  {lastCheck === 'full'
                    ? 'Выполнена полная проверка: хэши выпуска и запись в пользовательские каталоги.'
                    : 'Сейчас показана быстрая проверка без полного хэширования и без пробной записи. Полная проверка запускается только кнопкой выше.'}
                </p>
              </div>
            </section>

            <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
              <h2 className="text-lg font-semibold">Ресурсы компьютера</h2>
              <p className="mt-1 text-sm text-slate-500">
                Это справочная ёмкость для диагностики, а не искусственный минимальный порог. Конкретная нагрузка зависит от кодека, разрешения и длительности проекта.
              </p>
              <dl className="mt-4 grid gap-3 sm:grid-cols-3">
                <div className="rounded-xl bg-slate-950/70 p-4">
                  <dt className="text-xs text-slate-500">Логические CPU</dt>
                  <dd className="mt-1 text-lg font-semibold">{diagnostics.resources.logical_cpu_count ?? 'не определено'}</dd>
                </div>
                <div className="rounded-xl bg-slate-950/70 p-4">
                  <dt className="text-xs text-slate-500">Физическая память</dt>
                  <dd className="mt-1 text-lg font-semibold">{formatBytes(diagnostics.resources.memory.total_bytes)}</dd>
                </div>
                <div className="rounded-xl bg-slate-950/70 p-4">
                  <dt className="text-xs text-slate-500">Сейчас доступно RAM</dt>
                  <dd className="mt-1 text-lg font-semibold">{formatBytes(diagnostics.resources.memory.available_bytes)}</dd>
                </div>
              </dl>
            </section>

            <section className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
                <h2 className="text-lg font-semibold">Встроенные медиасредства</h2>
                <p className="mt-1 text-sm text-slate-500">В установленном выпуске используются только средства, зафиксированные в release manifest.</p>
                <div className="mt-4">
                  {media.map(([name, item]) => (
                    <div key={name} className="flex items-center justify-between border-b border-slate-800 py-3 last:border-b-0">
                      <span className="font-mono text-sm text-slate-300">{name}</span>
                      <span className={item.available ? 'text-sm text-emerald-300' : 'text-sm text-rose-300'}>
                        {item.available ? 'доступно' : 'недоступно'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
                <h2 className="text-lg font-semibold">Пользовательское хранилище</h2>
                <p className="mt-1 text-sm text-slate-500">Пробная запись выполняется только во время полной проверки; временный файл сразу удаляется.</p>
                <div className="mt-4">
                  <StorageLine label="Данные пользователя" value={diagnostics.storage.user_data} />
                  <StorageLine label="Project Store" value={diagnostics.storage.project_store} />
                  <StorageLine label="Конфигурация" value={diagnostics.storage.configuration} />
                </div>
              </div>
            </section>

            <section className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className="text-lg font-semibold">Снимки миграции</h2>
                    <p className="mt-1 text-sm text-slate-500">Метаданные восстановления проверяются по собственному манифесту и SHA-256.</p>
                  </div>
                  <span className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-400">
                    {recovery?.checked ? 'проверено' : 'не проверено'}
                  </span>
                </div>
                <dl className="mt-5 grid grid-cols-2 gap-3 text-sm">
                  <div className="rounded-xl bg-slate-950/70 p-4"><dt className="text-slate-500">Всего снимков</dt><dd className="mt-1 text-lg font-semibold">{recovery?.snapshot_count ?? '—'}</dd></div>
                  <div className="rounded-xl bg-slate-950/70 p-4"><dt className="text-slate-500">Валидных</dt><dd className="mt-1 text-lg font-semibold text-emerald-300">{recovery?.valid_snapshot_count ?? '—'}</dd></div>
                  <div className="rounded-xl bg-slate-950/70 p-4"><dt className="text-slate-500">Повреждённых</dt><dd className="mt-1 text-lg font-semibold">{recovery?.invalid_snapshot_count ?? '—'}</dd></div>
                  <div className="rounded-xl bg-slate-950/70 p-4"><dt className="text-slate-500">Незавершённых</dt><dd className="mt-1 text-lg font-semibold">{recovery?.incomplete_staging_count ?? '—'}</dd></div>
                </dl>
                <p className="mt-4 text-sm text-slate-500">Последний валидный снимок: {formatDate(recovery?.latest_created_at ?? null)}</p>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
                <h2 className="text-lg font-semibold">Резервная копия проекта</h2>
                <p className="mt-2 text-sm leading-6 text-slate-400">
                  Полная пользовательская резервная копия — файл <code className="rounded bg-slate-950 px-1.5 py-0.5 text-slate-300">.uvproj.zip</code>. Он включает проект и его файлы, проверяется по манифесту при импорте и не смешивается с автоматическими снимками миграции метаданных.
                </p>
                <div className="mt-5 flex flex-wrap gap-3">
                  <Link href="/projects" className="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-white">
                    Открыть проекты
                  </Link>
                  <Link href="/settings" className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:border-slate-500 hover:bg-slate-800">
                    Настройки
                  </Link>
                </div>
              </div>
            </section>

            {(diagnostics.issues.length > 0 || diagnostics.release.problems.length > 0) && (
              <section className="rounded-2xl border border-amber-800/60 bg-amber-950/20 p-5">
                <h2 className="text-lg font-semibold text-amber-200">Что требует внимания</h2>
                <div className="mt-4 space-y-3">
                  {diagnostics.issues.map(issue => (
                    <div key={issue.code} className="rounded-xl border border-amber-900/70 bg-slate-950/50 p-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-medium text-amber-200">{issue.message}</span>
                        <code className="text-xs text-slate-500">{issue.code}</code>
                      </div>
                    </div>
                  ))}
                  {diagnostics.release.problems.map(problem => (
                    <div key={problem} className="rounded-xl border border-rose-900/70 bg-slate-950/50 p-4 text-sm text-rose-200">
                      {problem}
                    </div>
                  ))}
                </div>
              </section>
            )}
          </div>
        ) : null}
      </div>
    </main>
  );
}
