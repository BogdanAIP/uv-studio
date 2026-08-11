export type PolicyMode = 'off' | 'optional' | 'required';

export interface ProductionPolicy {
  source_review: PolicyMode;
  direction_gate: PolicyMode;
  sample_first: PolicyMode;
  plan_gate: PolicyMode;
  scene_ledger: PolicyMode;
  final_review: PolicyMode;
  continuity: PolicyMode;
}

export interface RecipeStep {
  step_id: string;
  title: string;
  description: string;
  capability_id: string | null;
  optional: boolean;
}

export interface RecipeUIHints {
  category: string;
  primary_input_label: string;
  visible_sections: string[];
  advanced_sections: string[];
  featured: boolean;
}

export interface UVRecipe {
  schema_version: number;
  recipe_id: string;
  title: string;
  description: string;
  required_inputs: string[];
  optional_inputs: string[];
  required_capabilities: string[];
  optional_capabilities: string[];
  steps: RecipeStep[];
  production_policy: ProductionPolicy;
  ui: RecipeUIHints;
}

async function apiError(response: Response, fallback: string): Promise<Error> {
  const body = await response.json().catch(() => null);
  const detail = body && typeof body.detail === 'string' ? body.detail : fallback;
  return new Error(detail);
}

export async function listUVRecipes(): Promise<UVRecipe[]> {
  const response = await fetch('/api/uv/recipes', { cache: 'no-store' });
  if (!response.ok) throw await apiError(response, 'Failed to load recipes');
  return response.json();
}

export async function getUVRecipe(recipeId: string): Promise<UVRecipe> {
  const response = await fetch(`/api/uv/recipes/${encodeURIComponent(recipeId)}`, {
    cache: 'no-store',
  });
  if (!response.ok) throw await apiError(response, 'Failed to load recipe');
  return response.json();
}
