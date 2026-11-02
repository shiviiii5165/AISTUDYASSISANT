import { api } from './api';

export interface GamificationStreak {
  user_id: string;
  current_streak_days: number;
  longest_streak_days: number;
  last_activity_date: string | null;
  freeze_credits: number;
}

export interface GamificationBadge {
  badge_id: string;
  badge_name: string;
  description: string;
  icon_name: string;
  category: string;
  unlocked_at: string;
}

export interface GamificationSummary {
  user_id: string;
  total_xp: number;
  current_level: number;
  current_level_xp: number;
  next_level_xp: number;
  progress_to_next_level: number;
  streak: GamificationStreak;
  badges: GamificationBadge[];
}

export interface AwardXPRequest {
  activity_type: string;
  amount: number;
  reference_id: string;
  details?: Record<string, any>;
}

export interface AwardXPResponse {
  awarded: boolean;
  awarded_amount: number;
  new_total_xp: number;
  current_level: number;
  leveled_up: boolean;
  unlocked_badges: GamificationBadge[];
  message: string;
}

export async function fetchGamificationSummary(): Promise<GamificationSummary> {
  const response = await api.get<GamificationSummary>('/api/gamification/summary');
  return response.data;
}

export async function checkInStreak(): Promise<GamificationStreak> {
  const response = await api.post<GamificationStreak>('/api/gamification/streak/check-in');
  return response.data;
}

export async function awardXP(data: AwardXPRequest): Promise<AwardXPResponse> {
  const response = await api.post<AwardXPResponse>('/api/gamification/award', data);
  return response.data;
}

