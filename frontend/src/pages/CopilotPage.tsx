import { FormEvent, useEffect, useMemo, useState } from "react";

import { fetchCatalog, fetchHealth, postChat } from "../api/client";
import { ChatMessage } from "../components/ChatMessage";
import { SuggestedQuestions } from "../components/SuggestedQuestions";
import type { ChatMessage as ChatMessageModel, HealthResponse, MetricDefinition } from "../types";

const DEFAULT_QUESTIONS = [
  "今天交车多少？",
  "今天卖车同比多少？",
  "最近7天卖车趋势如何？",
  "各城市卖车排名？",
  "按渠道拆解今天交车量",
  "为什么今天卖车下降？",
];

const SESSION_ID = "demo-session-001";

export function CopilotPage() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessageModel[]>([
    {
      id: "welcome",
      role: "assistant",
      text: "欢迎使用 Auditable Business Metrics Copilot。你可以直接提业务问题，我会同时返回结果、SQL、指标口径和明细数据。",
    },
  ]);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [catalog, setCatalog] = useState<MetricDefinition[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHealth().then(setHealth).catch(() => undefined);
    fetchCatalog().then(setCatalog).catch(() => undefined);
  }, []);

  const catalogNames = useMemo(() => catalog.map((item) => item.name_zh).join(" / "), [catalog]);

  async function sendMessage(message: string) {
    if (!message.trim()) {
      return;
    }

    const userMessage: ChatMessageModel = {
      id: `user-${Date.now()}`,
      role: "user",
      text: message,
    };

    setMessages((current) => [...current, userMessage]);
    setLoading(true);
    setError(null);
    setInput("");

    try {
      const response = await postChat(SESSION_ID, message);
      const assistantMessage: ChatMessageModel = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        text: response.type === "answer" ? response.summary : response.message,
        response,
      };
      setMessages((current) => [...current, assistantMessage]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "请求失败");
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendMessage(input);
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-panel">
          <span className="eyebrow">BI Copilot</span>
          <h1>Auditable Business Metrics Copilot</h1>
          <p>可审计经营指标智能问答 Agent</p>
        </div>

        <div className="sidebar-panel">
          <div className="panel-title">推荐问题</div>
          <SuggestedQuestions onSelect={sendMessage} questions={DEFAULT_QUESTIONS} />
        </div>

        <div className="sidebar-panel">
          <div className="panel-title">系统状态</div>
          <div className="status-card">
            <div>
              <span className="status-label">Backend</span>
              <strong>{health?.status ?? "loading"}</strong>
            </div>
            <div>
              <span className="status-label">数据源</span>
              <strong>{health?.data_source ?? "--"}</strong>
            </div>
            <div>
              <span className="status-label">指标数</span>
              <strong>{health?.metrics_loaded ?? "--"}</strong>
            </div>
          </div>
        </div>

        <div className="sidebar-panel">
          <div className="panel-title">指标目录</div>
          <p className="catalog-preview">{catalogNames || "正在加载指标目录..."}</p>
        </div>
      </aside>

      <main className="chat-stage">
        <div className="chat-header">
          <div>
            <span className="eyebrow">Result Mode + Code Mode</span>
            <h2>统一指标、可审计 SQL、可追溯结果</h2>
          </div>
          <div className="header-badge">Session: {SESSION_ID}</div>
        </div>

        <div className="message-stream">
          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} onSelectClarification={sendMessage} />
          ))}
          {loading ? <div className="assistant-bubble pending">正在分析问题并生成审计结果...</div> : null}
        </div>

        <form className="composer" onSubmit={handleSubmit}>
          <textarea
            className="composer-input"
            onChange={(event) => setInput(event.target.value)}
            placeholder="例如：今天卖车同比多少？"
            rows={3}
            value={input}
          />
          <div className="composer-footer">
            {error ? <div className="error-banner">{error}</div> : <div className="hint">默认会同时返回结果与代码。</div>}
            <button className="primary-button" disabled={loading} type="submit">
              发送
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}

