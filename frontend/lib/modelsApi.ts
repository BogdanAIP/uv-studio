export interface ApiModelOption {
  id: string;
  label: string;
  provider: string;
  family?: string;
  media_type?: 'image' | 'video';
  model_type?: 'llm' | 'vlm' | 't2i' | 'i2i' | 'video';
  type?: string[];
  ability_type?: string;
  ability_types?: string[];
  adapter_ability_types?: string[];
  input_modalities?: string[];
  adapter_input_modalities?: string[];
  api_contract_verified?: boolean;
  capabilities?: Record<string, unknown>;
}

export async function fetchApiModels(
  params: {
    mediaType?: 'image' | 'video';
    modelType?: 'llm' | 'vlm' | 't2i' | 'i2i' | 'video';
    ability?: string;
    verifiedOnly?: boolean;
  } = {},
): Promise<ApiModelOption[]> {
  const search = new URLSearchParams();
  if (params.mediaType) search.set('media_type', params.mediaType);
  if (params.modelType) search.set('model_type', params.modelType);
  if (params.ability) search.set('ability', params.ability);
  if (params.verifiedOnly) search.set('verified_only', 'true');

  const query = search.toString();
  const suffix = query ? `?${query}` : '';
  const response = await fetch(`/api/models${suffix}`);
  if (!response.ok) {
    throw new Error('获取模型列表失败');
  }
  const data = await response.json();
  return data.models || [];
}
