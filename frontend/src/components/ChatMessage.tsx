import type { ChatMessage as ChatMessageModel } from "../types";
import { AssistantAnswerCard } from "./AssistantAnswerCard";

interface ChatMessageProps {
  message: ChatMessageModel;
  onSelectClarification: (value: string) => void;
}

export function ChatMessage({ message, onSelectClarification }: ChatMessageProps) {
  if (message.role === "user") {
    return (
      <div className="message-row user">
        <div className="user-bubble">{message.text}</div>
      </div>
    );
  }

  if (message.response?.type === "answer") {
    return (
      <div className="message-row assistant">
        <AssistantAnswerCard answer={message.response} />
      </div>
    );
  }

  return (
    <div className="message-row assistant">
      <div className="assistant-bubble">
        <p>{message.response?.type === "clarification" ? message.response.message : message.text}</p>
        {message.response?.type === "clarification" ? (
          <div className="option-grid">
            {message.response.options.map((option) => (
              <button
                className="option-chip"
                key={option}
                onClick={() => onSelectClarification(option)}
                type="button"
              >
                {option}
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

