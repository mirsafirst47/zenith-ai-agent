import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import { format, formatDistanceToNow } from 'date-fns'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDuration(seconds: number | null | undefined): string {
  if (!seconds) return 'N/A';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}m ${secs}s`;
}

export function formatTimestamp(timestamp: string | null | undefined): string {
  if (!timestamp) return 'N/A';
  try {
    return formatDistanceToNow(new Date(timestamp), { addSuffix: true });
  } catch {
    return 'Invalid date';
  }
}

export function formatDateTime(timestamp: string | null | undefined): string {
  if (!timestamp) return 'N/A';
  try {
    return format(new Date(timestamp), 'PPpp');
  } catch {
    return 'Invalid date';
  }
}

export function getLanguageFlag(lang: string | null | undefined): string {
  if (!lang) return '🌐';
  const flags: { [key: string]: string } = {
    'en': '🇺🇸',
    'es': '🇪🇸',
    'zh': '🇨🇳',
    'fr': '🇫🇷',
    'ru': '🇷🇺',
  };
  return flags[lang] || '🌐';
}

export function getLanguageName(lang: string | null | undefined): string {
  if (!lang) return 'Unknown';
  const names: { [key: string]: string } = {
    'en': 'English',
    'es': 'Spanish',
    'zh': 'Chinese',
    'fr': 'French',
    'ru': 'Russian',
  };
  return names[lang] || 'Unknown';
}
