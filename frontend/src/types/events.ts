export interface PrerakEvent {
  event_id: string;
  conversation_id: string;
  execution_id: string;
  timestamp: string;
  event_type: string;
  tool?: string;
  success?: boolean;
  path?: string;
  details?: Record<string, any>;
}
