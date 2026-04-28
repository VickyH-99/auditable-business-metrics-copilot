interface SuggestedQuestionsProps {
  questions: string[];
  onSelect: (question: string) => void;
}

export function SuggestedQuestions({ questions, onSelect }: SuggestedQuestionsProps) {
  return (
    <div className="suggestion-list">
      {questions.map((question) => (
        <button className="suggestion-card" key={question} onClick={() => onSelect(question)} type="button">
          <span className="suggestion-kicker">Suggested</span>
          <strong>{question}</strong>
        </button>
      ))}
    </div>
  );
}

