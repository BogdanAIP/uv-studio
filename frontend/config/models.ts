export interface ModelOption {
  id: string;
  label: string;
  default?: boolean;
}

export interface ProviderGroup {
  provider: string;
  label: string;
  models: ModelOption[];
}

export type VideoGenerationMode = 'first_frame' | 'start_end_frame' | 'reference';

export const VIDEO_GENERATION_MODES: Array<{
  id: VideoGenerationMode;
  label: string;
  ability: string;
  modelKey: string;
}> = [
  { id: 'first_frame', label: 'По первому кадру', ability: 'first_frame_i2v', modelKey: 'video_first_frame_model' },
  { id: 'start_end_frame', label: 'По первому и последнему кадру', ability: 'start_end_frame_i2v', modelKey: 'video_start_end_model' },
  { id: 'reference', label: 'По референсу', ability: 'reference_to_video', modelKey: 'video_reference_model' },
];

export function videoModeAbility(mode: string | undefined) {
  return VIDEO_GENERATION_MODES.find(item => item.id === mode)?.ability || 'first_frame_i2v';
}

export function videoModeModelKey(mode: string | undefined) {
  return VIDEO_GENERATION_MODES.find(item => item.id === mode)?.modelKey || 'video_first_frame_model';
}

export const STYLES = [
  { id: 'comic-book', label: 'Комикс' },
  { id: 'anime', label: 'Аниме' },
  { id: 'realistic', label: 'Реалистичный' },
  { id: '3d-disney', label: 'Стилизованная 3D-анимация' },
  { id: 'watercolor', label: 'Акварель' },
  { id: 'oil-painting', label: 'Масляная живопись' },
  { id: 'cyberpunk', label: 'Киберпанк' },
  { id: 'chinese-ink', label: 'Тушь' },
];

export const VIDEO_RATIOS = [
  { id: '16:9', label: '16:9', ratio: '16:9' },
  { id: '9:16', label: '9:16', ratio: '9:16' },
  { id: '1:1', label: '1:1', ratio: '1:1' },
  { id: '4:3', label: '4:3', ratio: '4:3' },
  { id: '3:4', label: '3:4', ratio: '3:4' },
  { id: '21:9', label: '21:9', ratio: '21:9' },
];

export const VIDEO_RESOLUTIONS = [
  { id: '720P', label: '720p' },
  { id: '1080P', label: '1080p' },
];
