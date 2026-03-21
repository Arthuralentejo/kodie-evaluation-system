export const API_BASE =  import.meta.env.VITE_API_BASE_URL ||  "http://localhost:8000";
export const STEP_COUNT = 5;

export const STAGES = {
  AUTH: "AUTH",
  INTRO: "INTRO",
  QUESTIONS: "QUESTIONS",
  REVIEW: "REVIEW",
  COMPLETED: "COMPLETED",
};

export const SESSION_KEY = "kodie.session";
