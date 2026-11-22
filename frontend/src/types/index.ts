export interface Conversation {
  id: number;
  title: string;
  conv_type: "chat" | "video";
  system_prompt: string;
  model: string;
  megapixels: number;
  steps: number;
  duration: number;
  keep_audio: boolean;
  parent_conversation_id: number | null;
  fork_from_message_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ChatChunk {
  content?: string;
  error?: string;
}

export interface ModelOption {
  id: string;
  label: string;
  context: number;
}
