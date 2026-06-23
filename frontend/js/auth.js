import { fetchCurrentUser, loginUser, registerUser } from "/js/api.js";

const SESSION_KEY = "movie-recommender-session";

export function getSession() {
  const raw = window.localStorage.getItem(SESSION_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw);
  } catch {
    window.localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

export function saveSession(session) {
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearSession() {
  window.localStorage.removeItem(SESSION_KEY);
}

export function logout() {
  clearSession();
  window.location.href = "/login.html";
}

export async function requireSession() {
  const session = getSession();
  if (!session?.access_token) {
    window.location.href = "/login.html";
    throw new Error("Sesión requerida.");
  }
  return session;
}

export async function resolveActiveUser() {
  const session = await requireSession();
  try {
    const response = await fetchCurrentUser(session.access_token);
    return { session, user: response.user };
  } catch (error) {
    clearSession();
    window.location.href = "/login.html";
    throw error;
  }
}

function setMessage(element, message, status = "") {
  if (!element) {
    return;
  }
  element.textContent = message;
  element.className = `inline-message ${status}`.trim();
}

function serializeForm(form) {
  return Object.fromEntries(new FormData(form).entries());
}

export function mountAuthPage() {
  const existingSession = getSession();
  if (existingSession?.access_token) {
    window.location.href = "/";
    return;
  }

  const loginForm = document.querySelector("#login-form");
  const registerForm = document.querySelector("#register-form");
  const loginMessage = document.querySelector("#login-message");
  const registerMessage = document.querySelector("#register-message");

  loginForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage(loginMessage, "Ingresando...");
    try {
      const payload = serializeForm(loginForm);
      const response = await loginUser(payload);
      saveSession(response);
      setMessage(loginMessage, "Sesión iniciada. Redirigiendo...", "success");
      window.location.href = "/";
    } catch (error) {
      setMessage(loginMessage, error.message, "danger");
    }
  });

  registerForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage(registerMessage, "Creando cuenta...");
    try {
      const payload = serializeForm(registerForm);
      const response = await registerUser(payload);
      saveSession(response);
      setMessage(registerMessage, "Cuenta creada. Redirigiendo...", "success");
      window.location.href = "/";
    } catch (error) {
      setMessage(registerMessage, error.message, "danger");
    }
  });
}
