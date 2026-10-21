import { useEffect, useState } from "react";
import { api } from "../lib/api";

export function CaptchaChallenge({ onChallenge, onAnswer }: {
  onChallenge: (challenge: string) => void;
  onAnswer: (answer: string) => void;
}) {
  const [question, setQuestion] = useState("");
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    if (typeof api.captchaChallenge !== "function") {
      setFailed(true);
      return () => { active = false; };
    }
    api.captchaChallenge().then(({ challenge, question: prompt }) => {
      if (!active) return;
      onChallenge(challenge);
      setQuestion(prompt);
      setFailed(false);
    }).catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [onChallenge]);
  if (failed) return <p className="text-sm text-error">Could not load CAPTCHA. Refresh the page to try again.</p>;
  if (!question) return <p className="text-sm opacity-70">Loading CAPTCHA…</p>;
  return <div>
    <label className="block text-sm mb-1" htmlFor="captcha-answer">{question}</label>
    <input id="captcha-answer" type="text" inputMode="numeric" pattern="\d{1,3}" maxLength={3}
      autoComplete="off" required onChange={(event) => onAnswer(event.target.value)}
      className="input input-bordered w-full bg-base-100" aria-label="CAPTCHA answer" />
  </div>;
}
