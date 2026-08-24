'use client';

import { useEffect, useMemo, useState } from 'react';
import { CheckCircle, Loader2, Save, Settings, XCircle } from 'lucide-react';
import {
  STYLES,
  VIDEO_GENERATION_MODES,
  VIDEO_RATIOS,
  VIDEO_RESOLUTIONS,
} from '@/config/models';

type ConfigTree = Record<string, unknown>;
type SecretStatus = Record<string, boolean>;

type CapabilitySummary = {
  capability_id: string;
  title: string;
  description: string;
  offer_summary: {
    total: number;
    available: number;
    configuration_required: number;
    unavailable: number;
  };
};

type ProviderDefinition = {
  id: string;
  title: string;
  description: string;
  keyPath: string;
  baseUrlPath: string;
  proxyPath: string;
};

const PROVIDERS: ProviderDefinition[] = [
  {
    id: 'openai',
    title: 'OpenAI',
    description: 'Подключение к OpenAI или совместимому API. Само наличие ключа не разрешает автоматический платный вызов.',
    keyPath: 'api_providers.openai.api_key',
    baseUrlPath: 'api_providers.openai.base_url',
    proxyPath: 'api_providers.openai.enable_proxy',
  },
  {
    id: 'gemini',
    title: 'Gemini',
    description: 'Подключение к Google Gemini. Используется только там, где соответствующая возможность будет явно разрешена.',
    keyPath: 'api_providers.gemini.api_key',
    baseUrlPath: 'api_providers.gemini.base_url',
    proxyPath: 'api_providers.gemini.enable_proxy',
  },
  {
    id: 'deepseek',
    title: 'DeepSeek',
    description: 'Подключение к DeepSeek для совместимых текстовых задач.',
    keyPath: 'api_providers.deepseek.api_key',
    baseUrlPath: 'api_providers.deepseek.base_url',
    proxyPath: 'api_providers.deepseek.enable_proxy',
  },
  {
    id: 'dashscope',
    title: 'DashScope',
    description: 'Alibaba Cloud DashScope, включая совместимые Qwen/Wan возможности.',
    keyPath: 'api_providers.dashscope.api_key',
    baseUrlPath: 'api_providers.dashscope.base_url',
    proxyPath: 'api_providers.dashscope.enable_proxy',
  },
  {
    id: 'ark',
    title: 'Volcengine ARK',
    description: 'Совместимый слой для Seedream/Seedance и других ARK-моделей.',
    keyPath: 'api_providers.ark.api_key',
    baseUrlPath: 'api_providers.ark.base_url',
    proxyPath: 'api_providers.ark.enable_proxy',
  },
  {
    id: 'kling',
    title: 'Kling',
    description: 'Подключение к сервису генерации видео Kling.',
    keyPath: 'api_providers.kling.api_key',
    baseUrlPath: 'api_providers.kling.base_url',
    proxyPath: 'api_providers.kling.enable_proxy',
  },
];

const CAPABILITY_ORDER = [
  'text.generate',
  'image.generate',
  'video.generate',
  'speech.synthesize',
  'speech.transcribe',
  'media.understand',
  'timeline.assemble',
];

const LOG_LEVEL_OPTIONS = [
  { id: 'DEBUG', label: 'DEBUG — максимально подробно' },
  { id: 'INFO', label: 'INFO — обычный режим' },
  { id: 'WARNING', label: 'WARNING — предупреждения и ошибки' },
  { id: 'ERROR', label: 'ERROR — только ошибки' },
  { id: 'CRITICAL', label: 'CRITICAL — только критические ошибки' },
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

function formatConfigPath(path: string) {
  return (path || 'data/config/runtime.json').replace(/\\/g, '/');
}

function capabilityStatus(capability: CapabilitySummary) {
  if (capability.offer_summary.available > 0) {
    return { label: 'Доступно сейчас', className: 'bg-emerald-50 text-emerald-700 border-emerald-200' };
  }
  if (capability.offer_summary.configuration_required > 0) {
    return { label: 'Нужна настройка', className: 'bg-amber-50 text-amber-700 border-amber-200' };
  }
  return { label: 'Пока недоступно', className: 'bg-gray-50 text-gray-500 border-gray-200' };
}

export default function SettingsPage() {
  const [config, setConfig] = useState<ConfigTree>({});
  const [path, setPath] = useState('data/config/runtime.json');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [secretStatus, setSecretStatus] = useState<SecretStatus>({});
  const [secretDrafts, setSecretDrafts] = useState<Record<string, string>>({});
  const [secretClears, setSecretClears] = useState<Record<string, boolean>>({});
  const [capabilities, setCapabilities] = useState<CapabilitySummary[]>([]);
  const [capabilitiesError, setCapabilitiesError] = useState('');

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError('');
      setCapabilitiesError('');
      try {
        const configResponse = await fetch('/api/config');
        if (!configResponse.ok) throw new Error('Не удалось загрузить настройки');
        const data = await configResponse.json();
        setConfig(data.config || {});
        setSecretStatus(data.secrets || {});
        setPath(data.path || 'data/config/runtime.json');
        setSecretDrafts({});
        setSecretClears({});
      } catch (loadError: unknown) {
        setError(errorMessage(loadError, 'Не удалось загрузить настройки'));
      }

      try {
        const capabilityResponse = await fetch('/api/uv/capabilities');
        if (!capabilityResponse.ok) throw new Error('Каталог возможностей недоступен');
        const capabilityData = await capabilityResponse.json();
        setCapabilities(Array.isArray(capabilityData) ? capabilityData : []);
      } catch (capabilityError: unknown) {
        setCapabilitiesError(errorMessage(capabilityError, 'Не удалось определить доступные возможности'));
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  const visibleCapabilities = useMemo(() => {
    const byId = new Map(capabilities.map(item => [item.capability_id, item]));
    return CAPABILITY_ORDER.map(id => byId.get(id)).filter((item): item is CapabilitySummary => Boolean(item));
  }, [capabilities]);

  const updateConfig = (fieldPath: string, value: unknown) => {
    setConfig(current => setValue(current, fieldPath, value));
  };

  const updateSecret = (fieldPath: string, raw: string) => {
    setSecretDrafts(current => ({ ...current, [fieldPath]: raw }));
    setSecretClears(current => ({ ...current, [fieldPath]: false }));
  };

  const toggleSecretClear = (fieldPath: string) => {
    setSecretClears(current => ({ ...current, [fieldPath]: !current[fieldPath] }));
    setSecretDrafts(current => ({ ...current, [fieldPath]: '' }));
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
      setPath(data.path || 'data/config/runtime.json');
      setSecretDrafts({});
      setSecretClears({});
      setMessage('Настройки сохранены');
    } catch (saveError: unknown) {
      setError(errorMessage(saveError, 'Не удалось сохранить настройки'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50/50">
      <main className="mx-auto w-full max-w-6xl px-6 pb-12 pt-10">
        <div className="mb-8 text-center">
          <div className="mb-3 inline-flex items-center gap-2">
            <Settings className="h-7 w-7 text-blue-500" />
            <h1 className="text-2xl font-bold text-gray-800">Настройки</h1>
          </div>
          <p className="mx-auto max-w-3xl text-sm leading-6 text-gray-500">
            Для локального монтажа и работы с уже готовыми материалами подключать облачный ИИ не обязательно. Внешние сервисы добавляются только для тех возможностей, которым действительно нужна модель.
          </p>
        </div>

        {loading ? (
          <div className="flex h-56 items-center justify-center rounded-2xl border border-gray-200 bg-white text-sm text-gray-400">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Загрузка настроек…
          </div>
        ) : (
          <div className="space-y-5">
            <section className="rounded-2xl border border-blue-200 bg-blue-50/70 p-5">
              <h2 className="text-base font-semibold text-gray-800">Как UV Studio выбирает инструменты</h2>
              <div className="mt-3 grid gap-3 text-sm leading-6 text-gray-600 md:grid-cols-3">
                <div className="rounded-xl border border-blue-100 bg-white/70 p-4">
                  <span className="font-semibold text-gray-800">1. Сначала задача</span>
                  <p className="mt-1">Проект запрашивает возможность: например, собрать видео, создать изображение или синтезировать речь.</p>
                </div>
                <div className="rounded-xl border border-blue-100 bg-white/70 p-4">
                  <span className="font-semibold text-gray-800">2. Локальное и бесплатное — безопасный автоматический выбор</span>
                  <p className="mt-1">Если есть подходящий локальный бесплатный инструмент, UV Studio может использовать его без перехода на платный облачный сервис.</p>
                </div>
                <div className="rounded-xl border border-blue-100 bg-white/70 p-4">
                  <span className="font-semibold text-gray-800">3. Облако — только явно</span>
                  <p className="mt-1">Сохранённый API-ключ лишь делает сервис доступным. Он не означает согласие на любой платный вызов и не должен молча становиться запасным вариантом.</p>
                </div>
              </div>
            </section>

            <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
              <div className="mb-4">
                <h2 className="text-sm font-semibold text-gray-800">Возможности этой установки</h2>
                <p className="mt-1 text-xs leading-5 text-gray-500">
                  Это фактический каталог backend UV Studio. Он показывает возможности, а не заставляет заранее выбирать конкретные модели.
                </p>
              </div>
              {capabilitiesError ? (
                <p className="text-sm text-amber-700">{capabilitiesError}</p>
              ) : visibleCapabilities.length === 0 ? (
                <p className="text-sm text-gray-500">Каталог возможностей пока пуст.</p>
              ) : (
                <div className="grid gap-3 md:grid-cols-2">
                  {visibleCapabilities.map(capability => {
                    const status = capabilityStatus(capability);
                    return (
                      <div key={capability.capability_id} className="rounded-xl border border-gray-200 p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <h3 className="text-sm font-semibold text-gray-800">{capability.title}</h3>
                            <p className="mt-1 text-xs leading-5 text-gray-500">{capability.description}</p>
                          </div>
                          <span className={`shrink-0 rounded-full border px-2.5 py-1 text-[11px] ${status.className}`}>
                            {status.label}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </section>

            <details className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
              <summary className="cursor-pointer text-sm font-semibold text-gray-800">Подключить внешний ИИ-сервис · необязательно</summary>
              <p className="mt-3 max-w-3xl text-xs leading-5 text-gray-500">
                Не нужно подключать все сервисы. Эти подключения пока обслуживают совместимые генеративные адаптеры во время миграции на единый Capability Registry. Выбор конкретной платной модели не является глобальной настройкой по умолчанию и должен происходить в контексте нужной возможности.
              </p>
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                {PROVIDERS.map(provider => {
                  const configured = Boolean(secretStatus[provider.keyPath]);
                  const clearPending = Boolean(secretClears[provider.keyPath]);
                  const draft = secretDrafts[provider.keyPath] ?? '';
                  return (
                    <div key={provider.id} className="rounded-xl border border-gray-200 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <h3 className="text-sm font-semibold text-gray-800">{provider.title}</h3>
                          <p className="mt-1 text-xs leading-5 text-gray-500">{provider.description}</p>
                        </div>
                        <span className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] ${configured && !clearPending ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                          {configured && !clearPending ? 'Ключ сохранён' : 'Не подключён'}
                        </span>
                      </div>
                      <div className="mt-4 flex gap-2">
                        <input
                          aria-label={`Ключ API ${provider.title}`}
                          type="password"
                          autoComplete="new-password"
                          value={draft}
                          onChange={event => updateSecret(provider.keyPath, event.target.value)}
                          placeholder={
                            clearPending
                              ? 'Ключ будет удалён после сохранения'
                              : configured
                                ? 'Введите новый ключ для замены'
                                : 'Введите API-ключ'
                          }
                          className="h-10 min-w-0 flex-1 rounded-lg border border-gray-200 bg-white px-3 font-mono text-sm text-gray-700 outline-none focus:border-blue-300"
                        />
                        {(configured || clearPending) && (
                          <button
                            type="button"
                            onClick={() => toggleSecretClear(provider.keyPath)}
                            className={`h-10 shrink-0 rounded-lg border px-3 text-xs transition ${
                              clearPending
                                ? 'border-amber-300 bg-amber-50 text-amber-700'
                                : 'border-gray-200 text-gray-500 hover:border-red-200 hover:bg-red-50 hover:text-red-600'
                            }`}
                          >
                            {clearPending ? 'Отменить' : 'Удалить'}
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </details>

            <details className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
              <summary className="cursor-pointer text-sm font-semibold text-gray-800">Расширенные параметры подключений</summary>
              <p className="mt-3 text-xs leading-5 text-gray-500">
                Эти поля нужны для совместимых endpoint-ов, прокси и нестандартной инфраструктуры. В обычной установке их менять не требуется.
              </p>
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <TextField
                  label="Общий прокси"
                  value={String(getValue(config, 'api_providers.common.proxy') ?? '')}
                  onChange={value => updateConfig('api_providers.common.proxy', value)}
                />
                <BooleanField
                  label="Записывать входные данные моделей в журнал"
                  value={Boolean(getValue(config, 'api_providers.common.print_model_input'))}
                  onChange={value => updateConfig('api_providers.common.print_model_input', value)}
                />
                {PROVIDERS.map(provider => (
                  <div key={provider.id} className="rounded-xl border border-gray-200 p-4">
                    <h3 className="text-sm font-semibold text-gray-800">{provider.title}</h3>
                    <div className="mt-3 space-y-3">
                      <TextField
                        label="Адрес API"
                        value={String(getValue(config, provider.baseUrlPath) ?? '')}
                        onChange={value => updateConfig(provider.baseUrlPath, value)}
                      />
                      <BooleanField
                        label="Использовать прокси"
                        value={Boolean(getValue(config, provider.proxyPath))}
                        onChange={value => updateConfig(provider.proxyPath, value)}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </details>

            <details className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
              <summary className="cursor-pointer text-sm font-semibold text-gray-800">Параметры генеративных адаптеров</summary>
              <p className="mt-3 text-xs leading-5 text-gray-500">
                Эти значения сохранены для совместимых генеративных путей. Они не означают, что любой текущий проект уже умеет автоматически генерировать медиа из текста.
              </p>
              <div className="mt-5 grid gap-3 md:grid-cols-2">
                <SelectField
                  label="Способ генерации видео"
                  value={String(getValue(config, 'generation.video_generation_mode') ?? '')}
                  options={VIDEO_GENERATION_MODES}
                  onChange={value => updateConfig('generation.video_generation_mode', value)}
                />
                <SelectField
                  label="Визуальный стиль"
                  value={String(getValue(config, 'generation.style') ?? '')}
                  options={STYLES}
                  onChange={value => updateConfig('generation.style', value)}
                />
                <SelectField
                  label="Соотношение сторон"
                  value={String(getValue(config, 'generation.video_ratio') ?? '')}
                  options={VIDEO_RATIOS}
                  onChange={value => updateConfig('generation.video_ratio', value)}
                />
                <SelectField
                  label="Разрешение видео"
                  value={String(getValue(config, 'generation.video_resolution') ?? '')}
                  options={VIDEO_RESOLUTIONS}
                  onChange={value => updateConfig('generation.video_resolution', value)}
                />
              </div>
            </details>

            <details className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
              <summary className="cursor-pointer text-sm font-semibold text-gray-800">Технические настройки локального сервера</summary>
              <p className="mt-3 text-xs leading-5 text-gray-500">
                В обычной установленной версии менять эти параметры не требуется. Локальный сервер должен оставаться доступным только на этом компьютере.
              </p>
              <div className="mt-5 grid gap-3 md:grid-cols-2">
                <TextField
                  label="Адрес сервера"
                  value={String(getValue(config, 'server.host') ?? '')}
                  onChange={value => updateConfig('server.host', value)}
                />
                <NumberField
                  label="Порт"
                  value={Number(getValue(config, 'server.port') ?? 0)}
                  onChange={value => updateConfig('server.port', value)}
                />
                <SelectField
                  label="Уровень журналирования"
                  value={String(getValue(config, 'server.log_level') ?? '')}
                  options={LOG_LEVEL_OPTIONS}
                  onChange={value => updateConfig('server.log_level', value)}
                />
                <BooleanField
                  label="Журнал запросов"
                  value={Boolean(getValue(config, 'server.access_log'))}
                  onChange={value => updateConfig('server.access_log', value)}
                />
              </div>
              <p className="mt-4 text-[11px] text-gray-400">Файл обычных настроек: <span className="font-mono">{formatConfigPath(path)}</span></p>
            </details>

            <div className="sticky bottom-4 flex items-center gap-3 rounded-2xl border border-gray-200 bg-white/95 p-3 shadow-lg backdrop-blur">
              {message && (
                <span className="flex items-center gap-1.5 text-sm text-green-600">
                  <CheckCircle className="h-4 w-4" />
                  {message}
                </span>
              )}
              {error && (
                <span className="flex items-center gap-1.5 text-sm text-red-600">
                  <XCircle className="h-4 w-4" />
                  {error}
                </span>
              )}
              <button
                onClick={save}
                disabled={saving}
                className="ml-auto flex items-center gap-2 rounded-xl bg-blue-500 px-5 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-600 disabled:cursor-not-allowed disabled:bg-gray-200"
              >
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                Сохранить настройки
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function TextField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="flex min-w-0 flex-col gap-1.5">
      <span className="text-xs font-medium text-gray-500">{label}</span>
      <input
        type="text"
        value={value}
        onChange={event => onChange(event.target.value)}
        className="h-10 rounded-lg border border-gray-200 bg-white px-3 text-sm text-gray-700 outline-none focus:border-blue-300"
      />
    </label>
  );
}

function NumberField({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) {
  return (
    <label className="flex min-w-0 flex-col gap-1.5">
      <span className="text-xs font-medium text-gray-500">{label}</span>
      <input
        type="number"
        value={Number.isFinite(value) ? value : 0}
        onChange={event => onChange(Number(event.target.value) || 0)}
        className="h-10 rounded-lg border border-gray-200 bg-white px-3 text-sm text-gray-700 outline-none focus:border-blue-300"
      />
    </label>
  );
}

function BooleanField({ label, value, onChange }: { label: string; value: boolean; onChange: (value: boolean) => void }) {
  return (
    <label className="flex min-w-0 flex-col gap-1.5">
      <span className="text-xs font-medium text-gray-500">{label}</span>
      <select
        value={String(value)}
        onChange={event => onChange(event.target.value === 'true')}
        className="h-10 rounded-lg border border-gray-200 bg-white px-3 text-sm text-gray-700 outline-none focus:border-blue-300"
      >
        <option value="true">Включено</option>
        <option value="false">Выключено</option>
      </select>
    </label>
  );
}

function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: Array<{ id: string; label: string }>;
  onChange: (value: string) => void;
}) {
  return (
    <label className="flex min-w-0 flex-col gap-1.5">
      <span className="text-xs font-medium text-gray-500">{label}</span>
      <select
        value={value}
        onChange={event => onChange(event.target.value)}
        className="h-10 rounded-lg border border-gray-200 bg-white px-3 text-sm text-gray-700 outline-none focus:border-blue-300"
      >
        {options.map(option => (
          <option key={option.id} value={option.id}>{option.label}</option>
        ))}
      </select>
    </label>
  );
}
