import { api } from './api';

export interface SpacedCard {
  id: string;
  user_id: string;
  skill_id: string;
  subject: string;
  card_type: string;
  front_prompt: string;
  back_solution: string;
  explanation?: string;
  repetition_number: number;
  interval_days: number;
  ease_factor: number;
  due_date: string;
  total_reviews: number;
  lapses: number;
}

export interface ReviewSubmission {
  card_id: string;
  rating: number; // 0 to 5
  response_time_ms?: number;
}

export interface ReviewResponse {
  card_id: string;
  rating: number;
  new_interval_days: number;
  new_ease_factor: number;
  new_due_date: string;
  xp_awarded: number;
}

export async function fetchReviewQueue(limit = 10): Promise<SpacedCard[]> {
  const response = await api.get<SpacedCard[]>(`/api/spaced-repetition/queue?limit=${limit}`);
  return response.data;
}

export async function submitCardReview(review: ReviewSubmission): Promise<ReviewResponse> {
  const response = await api.post<ReviewResponse>('/api/spaced-repetition/review', review);
  return response.data;
}

export async function seedSpacedCards(subject = 'Mathematics'): Promise<{ seeded_count: number; message: string }> {
  const response = await api.post<{ seeded_count: number; message: string }>(`/api/spaced-repetition/seed?subject=${encodeURIComponent(subject)}`);
  return response.data;
}

