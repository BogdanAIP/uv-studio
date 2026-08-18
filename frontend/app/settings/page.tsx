'use client';

import {
  CheckCircle2,
  KeyRound,
  Loader2,
  Save,
  Server,
  SlidersHorizontal,
  Video,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import {
  STYLES,
  VIDEO_GENERATION_MODES,
  VIDEO_RATIOS,
  VIDEO_RESOLUTIONS,
} from '@/config/models';

type ConfigTree = Record<string, unknown>;
type SecretStatus = Record<string, boolean>;

type ProviderDefinition = {
  id: string;
  title: string;
  description: string;
};

const PROVIDERS: ProviderDefinition[] = [
  { id: 'openai', title: 'OpenAI / совместимый API', description: 'Текстовые, визуальные и совместимые OpenAI endpoints.' },
  { id: 'gemini', title: 'Gemini', description: 'Модели Google Gemini и совместимые endpoints.' },
  { id: 'deepseek', title: 'DeepSeek', description: 'Текстовые модели DeepSeek.' },
  { id: 'dashscope', title: 'DashScope', description: 'Qwen и другие сервисы Alibaba Cloud.' },
  { id: 'ark', title: 'Volcengine Ark', description: 'Seedream / Seedance и совместимые модели.' },
  { id: 'kling', title: 'Kling', description: 'Генерация видео Kling.' },
];

const MODEL_FIELDS = [
  { path: 'models.llm', label: 'Текстовая модель', placeholder: 'например, gpt-5' },
  { path: 'models.vlm', label: 'Модель анализа изображений и видео', placeholder: 'ID модели' },
  { path: 'models.image_it2i', label: 'Редактирование изображений', placeholder: 'ID модели' },
  { path: 'models.image_t2i', label: 'Генерация изображений', placeholder: 'ID модели' },
  { path: 'models.video_first_frame', label: 'Видео по первому кадру', placeholder: 'ID модели' },
  { path: 'models.video_start_end', label: 'Видео по первому и последнему кадру', placeholder: 'ID модели' },
  { path: 'models.video_reference', label: 'Видео по референсу', placeholder: 'ID модели' },
];

function isConfigTree(value: unknown): value is ConfigTree {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function getValue(config: ConfigTree, path: string): unknown {
  let current: unknown = config;
  for (const key of path.split('.')) {
    if (!isConfigTree(current)) return undefined;
    current = current[key];
  }
  return current;
}

function textValue(config: ConfigTree, path: string): string {
  const value = getValue(config, path);
  if (value === undefined || value === null) return '';
  return String(value);
}

function booleanValue(config: ConfigTree, path: string): boolean {
  return Boolean(getValue(config, path));
}

function setValue(config: ConfigTree, path: string, value: unknown): ConfigTree {
  const next = structuredClone(config || {});
  const parts = path.split('.');
  let current: ConfigTree = next;
  for (const part of parts.slice(0, -1)) {
    const child = current[part];
    if (!isConfigTree(child)) current[part] = {};
    current = current[part] as ConfigTree;
  }
  current[parts[parts.length - 1]] = value;
  return next;
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error && error.message ? error.message : fallback;
}

export default function SettingsPage() {
  const [config, setConfig] = useState<ConfigTree>({});
  const [secretStatus, setSecretStatus] = useState<SecretStatus>({});
  const [secretDrafts, setSecretDrafts] = useState<Record<string, string>>({});
  const [secretClears, setSecretClears] = useState<Record<string, boolean>>({});
  const [path, setPath] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    fetch('/api/config', { cache: 'no-store' })
      .then(async response => {
        if (!response.ok) throw new Error('Не удалось прочитать настройки');
        return response.json();
      })
      .then(data => {
        if (!active) return;
        setConfig(data.config || {});
        setSecretStatus(data.secrets || {});
        setPath(data.path || '');
      })
      .catch(err => {
        if (active) setError(errorMessage(err, 'Не удалось прочитать настройки'));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const configuredConnections = useMemo(
    () => PROVIDERS.filter(provider => secretStatus[`api_providers.${provider.id}.api_key`]).length,
    [secretStatus],
  );

  const update = (fieldPath: string, value: unknown) => {
    setConfig(current => setValue(current, fieldPath, value));
    setMessage('');
  };

  const updateSecret = (fieldPath: string, value: string) => {
    setSecretDrafts(current => ({ ...current, [fieldPath]: value }));
    setSecretClears(current => ({ ...current, [fieldPath]: false }));
    setMessage('');
  };

  const toggleClearSecret = (fieldPath: string) => {
    setSecretClears(current => ({ ...current, [fieldPath]: !current[fieldPath] }));
    setSecretDrafts(current => ({ ...current, [fieldPath]: '' }));
    setMessage('');
  };

  const save = async () => {
    setSaving(true);
    setMessage('');
    setError('');
    try {
      const secretUpdates: Record<string, string | null> = {};
      for (const [secretPath, draft] of Object.entries(secretDrafts)) {
        const normalized = draft.trim();
        if (normalized) secretUpdates[secretPath] = normalized;
      }
      for (const [secretPath, clear] of Object.entries(secretClears)) {
        if (clear) secretUpdates[secretPath] = null;
      }

      const response = await fetch('/api/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ values: config, secret_updates: secretUpdates }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || 'Не удалось сохранить настройки');
      }
      const data = await response.json();
      setConfig(data.config || {});
      setSecretStatus(data.secrets || {});
      setPath(data.path || '');
      setSecretDrafts({});
      setSecretClears({});
      setMessage('Настройки сохранены');
    } catch (err) {
      setError(errorMessage(err, 'Не удалось сохранить настройки'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="min-h-screen px-5 py-8 sm:px-8 lg:px-10">
      <div className="mx-auto max-w-6xl">
        <header className="flex flex-col gap-5 border-b border-[var(--uv-border)] pb-8 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.2em] text-violet-300">UV Studio</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-[-0.03em] text-zinc-50">Настройки</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-500">
              Подключения к внешним сервисам и значения по умолчанию. Проекты не хранят API-ключи и не привязываются к конкретному поставщику.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void save()}
            disabled={saving || loading}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-violet-400 px-4 text-sm font-semibold text-zinc-950 transition hover:bg-violet-300 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-600"
          >
            {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
            {saving ? 'Сохраняем…' : 'Сохранить'}
          </button>
        </header>

        {error && <div className="mt-6 rounded-xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">{error}</div>}
        {message && <div className="mt-6 flex items-center gap-2 rounded-xl border border-emerald-400/20 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-200"><CheckCircle2 size={16} /> {message}</div>}

        {loading ? (
          <div className="mt-8 h-72 animate-pulse rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)]" />
        ) : (
          <div className="mt-8 space-y-6">
            <SettingsSection
              icon={KeyRound}
              title="Подключения"
              description={`${configuredConnections} из ${PROVIDERS.length} подключений содержат сохранённый ключ. Ключи остаются локальными и отображаются только как статус.`}
            >
              <div className="grid gap-3 lg:grid-cols-2">
                {PROVIDERS.map(provider => (
                  <ProviderCard
                    key={provider.id}
                    provider={provider}
                    config={config}
                    secretStatus={secretStatus}
                    secretDrafts={secretDrafts}
                    secretClears={secretClears}
                    onUpdate={update}
                    onSecretUpdate={updateSecret}
                    onSecretClear={toggleClearSecret}
                  />
                ))}
              </div>
            </SettingsSection>

            <SettingsSection
              icon={SlidersHorizontal}
              title="Модели по умолчанию"
              description="Укажите ID моделей, которые должны предлагаться по умолчанию. Список не зависит от старого каталога моделей и не блокирует сохранение настроек."
            >
              <div className="grid gap-4 md:grid-cols-2">
                {MODEL_FIELDS.map(field => (
                  <Field key={field.path} label={field.label}>
                    <input
                      value={textValue(config, field.path)}
                      onChange={event => update(field.path, event.target.value)}
                      placeholder={field.placeholder}
                      className="uv-input"
                    />
                  </Field>
                ))}
              </div>
            </SettingsSection>

            <SettingsSection
              icon={Video}
              title="Видео по умолчанию"
              description="Базовые параметры для новых генеративных задач. Конкретный проект может использовать свои значения."
            >
              <div className="grid gap-4 md:grid-cols-2">
                <Field label="Способ генерации видео">
                  <select value={textValue(config, 'generation.video_generation_mode')} onChange={event => update('generation.video_generation_mode', event.target.value)} className="uv-input">
                    {VIDEO_GENERATION_MODES.map(option => <option key={option.id} value={option.id}>{option.label}</option>)}
                  </select>
                </Field>
                <Field label="Визуальный стиль">
                  <select value={textValue(config, 'generation.style')} onChange={event => update('generation.style', event.target.value)} className="uv-input">
                    {STYLES.map(option => <option key={option.id} value={option.id}>{option.label}</option>)}
                  </select>
                </Field>
                <Field label="Соотношение сторон">
                  <select value={textValue(config, 'generation.video_ratio')} onChange={event => update('generation.video_ratio', event.target.value)} className="uv-input">
                    {VIDEO_RATIOS.map(option => <option key={option.id} value={option.id}>{option.label}</option>)}
                  </select>
                </Field>
                <Field label="Разрешение">
                  <select value={textValue(config, 'generation.video_resolution')} onChange={event => update('generation.video_resolution', event.target.value)} className="uv-input">
                    {VIDEO_RESOLUTIONS.map(option => <option key={option.id} value={option.id}>{option.label}</option>)}
                  </select>
                </Field>
              </div>
            </SettingsSection>

            <details className="group rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)]">
              <summary className="flex cursor-pointer list-none items-center gap-3 px-5 py-4 text-sm text-zinc-400 transition hover:text-zinc-200">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/[0.035] text-zinc-600"><Server size={16} /></span>
                <div className="min-w-0 flex-1">
                  <p className="font-medium">Расширенные настройки приложения</p>
                  <p className="mt-0.5 text-xs text-zinc-700">Сеть, журналирование и общий прокси. Обычно менять не требуется.</p>
                </div>
                <span className="text-xs text-zinc-700 group-open:hidden">Показать</span>
              </summary>
              <div className="grid gap-4 border-t border-[var(--uv-border)] px-5 py-5 md:grid-cols-2">
                <Field label="Адрес локального сервера">
                  <input value={textValue(config, 'server.host')} onChange={event => update('server.host', event.target.value)} className="uv-input" />
                </Field>
                <Field label="Порт">
                  <input type="number" value={textValue(config, 'server.port')} onChange={event => update('server.port', Number(event.target.value) || 0)} className="uv-input" />
                </Field>
                <Field label="Уровень журнала">
                  <select value={textValue(config, 'server.log_level')} onChange={event => update('server.log_level', event.target.value)} className="uv-input">
                    <option value="DEBUG">Подробный (DEBUG)</option>
                    <option value="INFO">Обычный (INFO)</option>
                    <option value="WARNING">Предупреждения (WARNING)</option>
                    <option value="ERROR">Только ошибки (ERROR)</option>
                    <option value="CRITICAL">Критические ошибки (CRITICAL)</option>
                  </select>
                </Field>
                <Field label="Общий прокси">
                  <input value={textValue(config, 'api_providers.common.proxy')} onChange={event => update('api_providers.common.proxy', event.target.value)} placeholder="http://127.0.0.1:..." className="uv-input" />
                </Field>
                <Toggle checked={booleanValue(config, 'server.access_log')} onChange={value => update('server.access_log', value)} label="Журнал HTTP-запросов" />
                <Toggle checked={booleanValue(config, 'api_providers.common.print_model_input')} onChange={value => update('api_providers.common.print_model_input', value)} label="Печатать входные данные моделей в журнал" />
              </div>
            </details>

            {path && <p className="px-1 text-[10px] text-zinc-800">Локальная конфигурация: {path.replace(/\\/g, '/')}</p>}
          </div>
        )}
      </div>

      <style jsx global>{`
        .uv-input {
          width: 100%;
          border: 1px solid var(--uv-border);
          border-radius: 10px;
          background: rgba(0, 0, 0, 0.18);
          padding: 10px 12px;
          color: #e4e4e7;
          font-size: 13px;
          transition: border-color 120ms ease, background 120ms ease;
        }
        .uv-input:focus { border-color: rgba(139, 124, 246, 0.58); background: rgba(0, 0, 0, 0.24); }
        .uv-input::placeholder { color: #3f3f46; }
      `}</style>
    </main>
  );
}

function SettingsSection({ icon: Icon, title, description, children }: { icon: typeof KeyRound; title: string; description: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-5 sm:p-6">
      <div className="mb-5 flex items-start gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-violet-400/10 text-violet-300"><Icon size={17} /></span>
        <div>
          <h2 className="text-base font-medium text-zinc-100">{title}</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-zinc-600">{description}</p>
        </div>
      </div>
      {children}
    </section>
  );
}

function ProviderCard({
  provider,
  config,
  secretStatus,
  secretDrafts,
  secretClears,
  onUpdate,
  onSecretUpdate,
  onSecretClear,
}: {
  provider: ProviderDefinition;
  config: ConfigTree;
  secretStatus: SecretStatus;
  secretDrafts: Record<string, string>;
  secretClears: Record<string, boolean>;
  onUpdate: (path: string, value: unknown) => void;
  onSecretUpdate: (path: string, value: string) => void;
  onSecretClear: (path: string) => void;
}) {
  const prefix = `api_providers.${provider.id}`;
  const secretPath = `${prefix}.api_key`;
  const configured = Boolean(secretStatus[secretPath]) && !secretClears[secretPath];
  return (
    <div className="rounded-xl border border-[var(--uv-border)] bg-[var(--uv-surface-1)] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-medium text-zinc-200">{provider.title}</h3>
          <p className="mt-1 text-xs leading-5 text-zinc-700">{provider.description}</p>
        </div>
        <span className={`shrink-0 rounded-full px-2 py-1 text-[10px] ${configured ? 'bg-emerald-400/10 text-emerald-300' : 'bg-black/20 text-zinc-700'}`}>
          {configured ? 'Ключ сохранён' : 'Не подключено'}
        </span>
      </div>
      <div className="mt-4 space-y-3">
        <Field label="API-ключ">
          <input
            type="password"
            autoComplete="off"
            value={secretDrafts[secretPath] ?? ''}
            onChange={event => onSecretUpdate(secretPath, event.target.value)}
            placeholder={configured ? 'Сохранён · введите новый для замены' : 'Введите ключ'}
            className="uv-input"
          />
        </Field>
        {configured && (
          <label className="flex items-center gap-2 text-[11px] text-zinc-700">
            <input type="checkbox" checked={Boolean(secretClears[secretPath])} onChange={() => onSecretClear(secretPath)} />
            Удалить сохранённый ключ при сохранении
          </label>
        )}
        <details className="rounded-lg border border-[var(--uv-border)] bg-black/10 px-3 py-2">
          <summary className="cursor-pointer text-xs text-zinc-600">Дополнительно</summary>
          <div className="mt-3 space-y-3">
            <Field label="Base URL">
              <input value={textValue(config, `${prefix}.base_url`)} onChange={event => onUpdate(`${prefix}.base_url`, event.target.value)} placeholder="Оставьте пустым для стандартного адреса" className="uv-input" />
            </Field>
            <Toggle checked={booleanValue(config, `${prefix}.enable_proxy`)} onChange={value => onUpdate(`${prefix}.enable_proxy`, value)} label="Использовать общий прокси" />
          </div>
        </details>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block text-xs text-zinc-500"><span className="mb-2 block">{label}</span>{children}</label>;
}

function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (value: boolean) => void; label: string }) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-4 rounded-lg border border-[var(--uv-border)] bg-black/10 px-3 py-2.5 text-xs text-zinc-500">
      <span>{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative h-5 w-9 rounded-full transition ${checked ? 'bg-violet-400' : 'bg-zinc-800'}`}
      >
        <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition ${checked ? 'left-[18px]' : 'left-0.5'}`} />
      </button>
    </label>
  );
}
