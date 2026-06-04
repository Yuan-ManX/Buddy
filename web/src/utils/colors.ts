/** Shared role-to-color mappings used across Buddy UI components. */

const ROLE_COLORS: Record<string, string> = {
  strategy: '#3b82f6',
  engineering: '#10b981',
  research: '#8b5cf6',
  companion: '#f59e0b',
  custom: '#6b7280',
};

const ROLE_SECONDARY: Record<string, string> = {
  strategy: '#93c5fd',
  engineering: '#6ee7b7',
  research: '#c4b5fd',
  companion: '#fcd34d',
  custom: '#d1d5db',
};

export function getRoleColor(role: string): string {
  return ROLE_COLORS[role] || ROLE_COLORS.custom;
}

export function getRoleColorSecondary(role: string): string {
  return ROLE_SECONDARY[role] || ROLE_SECONDARY.custom;
}