'use client';

import { useEffect, useState } from 'react';
import { CheckCircle, Loader2, Save, Settings, XCircle } from 'lucide-react';
import { fetchModelGroupsByType, fetchVideoModelGroupsByAbility } from '@/lib/modelRegistry';
import {
  VIDEO_RATIOS,
  VIDEO_RESOLUTIONS,
  VIDEO_GENERATION_MODES,
  STYLES,
  type ProviderGroup,
} from '@/config/models';

type ConfigTree = Record<string, unknown>;
type SecretStatus = Record<string, boolean>;

type Field = {
  path: string;
  label: string;
  type?: 'text' | 'number' | 'boolean' | 'password' | 'select';
  options?: Array<{ id: string; label: string }> | ProviderGroup[];
};

type ModelSelectKey =
  | 'llm'
  | 'vlm'
  | 'image_it2i'
  | 'image_t2i'
  | 'video_first_frame'
  | 'video_start_end'
  | 'video_reference';

const EMPTY_MODEL_SELECTS: Record<ModelSelectKey, ProviderGroup[]> = {
  llm: [],
  vlm: [],
  image_it2i: [],
  image_t2i: [],
  video_first_frame: [],
  video_start_end: [],
  video_reference: [],
};

const LOG_LEVEL_OPTIONS = [
  { id: 'DEBUG', label: 'DEBUG — максимально подробно' },
  { id: 'INFO', label: 'INFO — обычный режим' },
  { id: 'WARNING', label: 'WARNING — предупреждения и ошибки' },
  { id: 'ERROR', label: 'ERROR — только ошибки' },
  { id: 'CRITICAL', label: 'CRITICAL — только критические ошибки' },
];

const GROUPS: Array<{ title: string; description: string; fields: Field[] }> = [
  {
    title: 'Сервер API',
    description: 'Параметры запуска локального сервера и журналирования. Для безопасности сервер должен оставаться доступным только на этом компьютере.',
    fields: [
      { path: 'server.host', label: 'Адрес сервера (host)' },
      { path: 'server.port', label: 'Порт', type: 'number' },
      { path: 'server.log_level', label: 'Уровень журналирования', type: 'select', options: LOG_LEVEL_OPTIONS },
      { path: 'server.access_log', label: 'Журнал запросов', type: 'boolean' },
    ],
  },
  {
    title: 'Общие настройки поставщиков ИИ',
    description: 'Общие параметры вызова моделей и сетевого прокси.',
    fields: [
      { path: 'api_providers.common.print_model_input', label: 'Записывать входные данные моделей в журнал', type: 'boolean' },
      { path: 'api_providers.common.proxy', label: 'Адрес прокси' },
    ],
  },
  {
    title: 'OpenAI',
    description: 'Настройки OpenAI и совместимых с OpenAI интерфейсов. Ключ хранится отдельно и никогда не читается обратно в браузер.',
    fields: [
      { path: 'api_providers.openai.api_key', label: 'Ключ API', type: 'password' },
      { path: 'api_providers.openai.base_url', label: 'Адрес API (base_url)' },
      { path: 'api_providers.openai.enable_proxy', label: 'Использовать прокси', type: 'boolean' },
    ],
  },
  {
    title: 'Gemini',
    description: 'Настройки Gemini и совместимых интерфейсов. Ключ хранится отдельно и никогда не читается обратно в браузер.',
    fields: [
      { path: 'api_providers.gemini.api_key', label: 'Ключ API', type: 'password' },
      { path: 'api_providers.gemini.base_url', label: 'Адрес API (base_url)' },
      { path: 'api_providers.gemini.enable_proxy', label: 'Использовать прокси', type: 'boolean' },
    ],
  },
  {
    title: 'DeepSeek',
    description: 'Настройки DeepSeek. Ключ хранится отдельно и никогда не читается обратно в браузер.',
    fields: [
      { path: 'api_providers.deepseek.api_key', label: 'Ключ API', type: 'password' },
      { path: 'api_providers.deepseek.base_url', label: 'Адрес API (base_url)' },
      { path: 'api_providers.deepseek.enable_proxy', label: 'Использовать прокси', type: 'boolean' },
    ],
  },
  {
    title: 'DashScope',
    description: 'Настройки сервисов Alibaba Cloud DashScope, включая модели Qwen и Wan. Ключ хранится отдельно и никогда не читается обратно в браузер.',
    fields: [
      { path: 'api_providers.dashscope.api_key', label: 'Ключ API', type: 'password' },
      { path: 'api_providers.dashscope.base_url', label: 'Адрес API (base_url)' },
      { path: 'api_providers.dashscope.enable_proxy', label: 'Использовать прокси', type: 'boolean' },
    ],
  },
  {
    title: 'ARK',
    description: 'Настройки Volcengine ARK для Seedream и Seedance. Ключ хранится отдельно и никогда не читается обратно в браузер.',
    fields: [
      { path: 'api_providers.ark.api_key', label: 'Ключ API', type: 'password' },
      { path: 'api_providers.ark.base_url', label: 'Адрес API (base_url)' },
      { path: 'api_providers.ark.enable_proxy', label: 'Использовать прокси', type: 'boolean' },
    ],
  },
  {
    title: 'Kling',
    description: 'Настройки сервиса генерации видео Kling. Ключ хранится отдельно и никогда не читается обратно в браузер.',
    fields: [
      { path: 'api_providers.kling.base_url', label: 'Адрес API (base_url)' },
      { path: 'api_providers.kling.api_key', label: 'Ключ API', type: 'password' },
      { path: 'api_providers.kling.enable_proxy', label: 'Использовать прокси', type: 'boolean' },
    ],
  },
  {
    title: 'Модели по умолчанию',
    description: 'Модели, которые основной рабочий процесс и разрешённые адаптеры поставщиков используют по умолчанию.',
    fields: [
      { path: 'models.llm', label: 'Текстовая модель (LLM)', type: 'select', options: [] },
      { path: 'models.vlm', label: 'Визуально-языковая модель (VLM)', type: 'select', options: [] },
      { path: 'models.image_it2i', label: 'Редактирование изображения по изображению', type: 'select', options: [] },
      { path: 'models.image_t2i', label: 'Генерация изображения по тексту', type: 'select', options: [] },
      { path: 'models.video_first_frame', label: 'Видео по первому кадру', type: 'select', options: [] },
      { path: 'models.video_start_end', label: 'Видео по первому и последнему кадрам', type: 'select', options: [] },
      { path: 'models.video_reference', label: 'Видео по референсному изображению', type: 'select', options: [] },
    ],
  },
  {
    title: 'Генерация видео',
    description: 'Способ генерации по умолчанию, визуальный стиль, соотношение сторон и разрешение видео.',
    fields: [
      { path: 'generation.video_generation_mode', label: 'Способ генерации видео', type: 'select', options: VIDEO_GENERATION_MODES },
      { path: 'generation.style', label: 'Визуальный стиль', type: 'select', options: STYLES },
      { path: 'generation.video_ratio', label: 'Соотношение сторон', type: 'select', options: VIDEO_RATIOS },
      { path: 'generation.video_resolution', label: 'Разрешение видео', type: 'select', options: VIDEO_RESOLUTIONS },
    ],
  },
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

function isProviderOptions(options: Field['options']): options is ProviderGroup[] {
  return Array.isArray(options) && options.some(option => 'models' in option);
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
  const [modelSelects, setModelSelects] = useState<Record<ModelSelectKey, ProviderGroup[]>>(EMPTY_MODEL_SELECTS);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const resp = await fetch('/api/config');
        if (!resp.ok) throw new Error('Не удалось загрузить настройки');
        const data = await resp.json();
        setConfig(data.config || {});
        setSecretStatus(data.secrets || {});
        setPath(data.path || 'data/config/runtime.json');
        setSecretDrafts({});
        setSecretClears({});
      } catch (loadError: unknown) {
        setError(errorMessage(loadError, 'Не удалось загрузить настройки'));
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetchModelGroupsByType('llm'),
      fetchModelGroupsByType('vlm'),
      fetchModelGroupsByType('i2i'),
      fetchModelGroupsByType('t2i'),
      fetchVideoModelGroupsByAbility('first_frame_i2v'),
      fetchVideoModelGroupsByAbility('start_end_frame_i2v'),
      fetchVideoModelGroupsByAbility('reference_to_video'),
    ])
      .then(([llm, vlm, imageIt2i, imageT2i, firstFrameVideo, startEndVideo, referenceVideo]) => {
        if (cancelled) return;
        setModelSelects({
          llm,
          vlm,
          image_it2i: imageIt2i,
          image_t2i: imageT2i,
          video_first_frame: firstFrameVideo,
          video_start_end: startEndVideo,
          video_reference: referenceVideo,
        });
      })
      .catch(() => {
        // Legacy /api/models intentionally remains unavailable while provider
        // routes move behind the UV Studio capability/authorization layer.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const groups = GROUPS.map(group => {
    if (group.title !== 'Модели по умолчанию') return group;
    return {
      ...group,
      fields: group.fields.map(field => {
        if (field.path === 'models.llm') return { ...field, options: modelSelects.llm };
        if (field.path === 'models.vlm') return { ...field, options: modelSelects.vlm };
        if (field.path === 'models.image_it2i') return { ...field, options: modelSelects.image_it2i };
        if (field.path === 'models.image_t2i') return { ...field, options: modelSelects.image_t2i };
        if (field.path === 'models.video_first_frame') return { ...field, options: modelSelects.video_first_frame };
        if (field.path === 'models.video_start_end') return { ...field, options: modelSelects.video_start_end };
        if (field.path === 'models.video_reference') return { ...field, options: modelSelects.video_reference };
        return field;
      }),
    };
  });

  const updateField = (field: Field, raw: string | boolean) => {
    const value = field.type === 'number' ? Number(raw) || 0 : raw;
    setConfig(current => setValue(current, field.path, value));
  };

  const updateSecretField = (field: Field, raw: string) => {
    setSecretDrafts(current => ({ ...current, [field.path]: raw }));
    setSecretClears(current => ({ ...current, [field.path]: false }));
  };

  const toggleSecretClear = (field: Field) => {
    setSecretClears(current => ({ ...current, [field.path]: !current[field.path] }));
    setSecretDrafts(current => ({ ...current, [field.path]: '' }));
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

      const resp = await fetch('/api/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ values: config, secret_updates: secretUpdates }),
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.detail || 'Не удалось сохранить настройки');
      }
      const data = await resp.json();
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
      <main className="w-full max-w-6xl mx-auto px-6 pt-10 pb-12">
        <div className="mb-8 text-center">
          <div className="inline-flex items-center gap-2 mb-3">
            <Settings className="w-7 h-7 text-blue-500" />
            <h1 className="text-2xl font-bold text-gray-800">Настройки</h1>
          </div>
          <p className="text-sm text-gray-500">
            Обычные параметры сохраняются в <span className="font-mono">{formatConfigPath(path)}</span>. Ключи API хранятся отдельно и не возвращаются из локального сервера в интерфейс.
          </p>
        </div>

        {loading ? (
          <div className="h-56 rounded-2xl border border-gray-200 bg-white flex items-center justify-center text-sm text-gray-400">
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Загрузка настроек…
          </div>
        ) : (
          <div className="space-y-5">
            {groups.map(group => (
              <section key={group.title} className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
                <div className="mb-4">
                  <h2 className="text-sm font-semibold text-gray-800">{group.title}</h2>
                  <p className="mt-1 text-xs text-gray-500">{group.description}</p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {group.fields.map(field => {
                    const value = getValue(config, field.path);
                    const configuredSecret = Boolean(secretStatus[field.path]);
                    const clearPending = Boolean(secretClears[field.path]);
                    const secretDraft = secretDrafts[field.path] ?? '';
                    return (
                      <label key={field.path} className="flex flex-col gap-1.5 min-w-0">
                        <span className="text-xs font-medium text-gray-500">{field.label}</span>
                        {field.type === 'boolean' ? (
                          <select
                            value={String(Boolean(value))}
                            onChange={event => updateField(field, event.target.value === 'true')}
                            className="h-10 rounded-lg border border-gray-200 bg-white px-3 text-sm text-gray-700 outline-none focus:border-blue-300"
                          >
                            <option value="true">Включено</option>
                            <option value="false">Выключено</option>
                          </select>
                        ) : field.type === 'select' ? (
                          <select
                            value={String(value ?? '')}
                            onChange={event => updateField(field, event.target.value)}
                            className="h-10 rounded-lg border border-gray-200 bg-white px-3 text-sm text-gray-700 outline-none focus:border-blue-300"
                          >
                            {isProviderOptions(field.options) ? (
                              field.options.map(providerGroup => (
                                <optgroup key={providerGroup.provider} label={providerGroup.label}>
                                  {providerGroup.models.map(model => (
                                    <option key={model.id} value={model.id}>{model.label}</option>
                                  ))}
                                </optgroup>
                              ))
                            ) : (
                              (field.options as Array<{ id: string; label: string }> | undefined || []).map(option => (
                                <option key={option.id} value={option.id}>{option.label}</option>
                              ))
                            )}
                          </select>
                        ) : field.type === 'password' ? (
                          <div className="flex gap-2">
                            <input
                              type="password"
                              autoComplete="new-password"
                              value={secretDraft}
                              onChange={event => updateSecretField(field, event.target.value)}
                              placeholder={
                                clearPending
                                  ? 'Ключ будет удалён после сохранения'
                                  : configuredSecret
                                    ? 'Ключ настроен — введите новый для замены'
                                    : 'Введите новый ключ'
                              }
                              className="h-10 min-w-0 flex-1 rounded-lg border border-gray-200 bg-white px-3 font-mono text-sm text-gray-700 outline-none focus:border-blue-300"
                            />
                            {(configuredSecret || clearPending) && (
                              <button
                                type="button"
                                onClick={() => toggleSecretClear(field)}
                                className={`h-10 shrink-0 rounded-lg border px-3 text-xs transition ${
                                  clearPending
                                    ? 'border-amber-300 bg-amber-50 text-amber-700 hover:bg-amber-100'
                                    : 'border-gray-200 text-gray-500 hover:border-red-200 hover:bg-red-50 hover:text-red-600'
                                }`}
                              >
                                {clearPending ? 'Отменить удаление' : 'Удалить'}
                              </button>
                            )}
                          </div>
                        ) : (
                          <input
                            type={field.type === 'number' ? 'number' : 'text'}
                            value={String(value ?? '')}
                            onChange={event => updateField(field, event.target.value)}
                            className="h-10 rounded-lg border border-gray-200 bg-white px-3 text-sm text-gray-700 outline-none focus:border-blue-300"
                          />
                        )}
                        {field.type === 'password' && configuredSecret && !clearPending && !secretDraft && (
                          <span className="text-[11px] text-green-600">Ключ настроен. Исходное значение не передаётся обратно в интерфейс.</span>
                        )}
                        {field.type === 'password' && clearPending && (
                          <span className="text-[11px] text-amber-600">Ключ будет удалён после сохранения настроек.</span>
                        )}
                      </label>
                    );
                  })}
                </div>
              </section>
            ))}

            <div className="sticky bottom-4 flex items-center gap-3 rounded-2xl border border-gray-200 bg-white/95 p-3 shadow-lg backdrop-blur">
              {message && (
                <span className="flex items-center gap-1.5 text-sm text-green-600">
                  <CheckCircle className="w-4 h-4" />
                  {message}
                </span>
              )}
              {error && (
                <span className="flex items-center gap-1.5 text-sm text-red-600">
                  <XCircle className="w-4 h-4" />
                  {error}
                </span>
              )}
              <button
                onClick={save}
                disabled={saving}
                className="ml-auto flex items-center gap-2 rounded-xl bg-blue-500 px-5 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-600 disabled:cursor-not-allowed disabled:bg-gray-200"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Сохранить настройки
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
