export interface Conversation {
  id: number;
  title: string;
  system_prompt: string;
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
