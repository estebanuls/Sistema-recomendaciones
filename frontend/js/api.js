const API_BASE =
  window.location.protocol.startsWith("http")
    ? window.location.origin
    : "http://127.0.0.1:8000";

async function request(path, { method = "GET", token, body } = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail || "Error inesperado al consultar la API.";
    throw new Error(Array.isArray(detail) ? JSON.stringify(detail) : detail);
  }
  return payload;
}

export async function loginUser(credentials) {
  return request("/api/auth/login", { method: "POST", body: credentials });
}

export async function registerUser(payload) {
  return request("/api/auth/register", { method: "POST", body: payload });
}

export async function fetchCurrentUser(token) {
  return request("/api/auth/me", { token });
}

export async function fetchMovies(query = "", limit = 12) {
  const searchParams = new URLSearchParams({ limit: String(limit) });
  if (query.trim()) {
    searchParams.set("query", query.trim());
  }
  return request(`/api/movies?${searchParams.toString()}`);
}

export async function fetchMovie(movieId) {
  return request(`/api/movies/${movieId}`);
}

export async function fetchRecommendations(token, limit = 10) {
  return request(`/api/recommendations?limit=${limit}`, { token });
}

export async function rateMovie(token, movieId, rating) {
  return request("/api/interactions/rate", {
    method: "POST",
    token,
    body: { movie_id: movieId, rating },
  });
}

export async function likeMovie(token, movieId, liked) {
  return request("/api/interactions/like", {
    method: "POST",
    token,
    body: { movie_id: movieId, liked },
  });
}

export async function fetchHistory(token, limit = 25) {
  return request(`/api/interactions/history?limit=${limit}`, { token });
}

export async function fetchProfile(token) {
  return request("/api/users/profile", { token });
}

export async function fetchOverview() {
  return request("/api/metrics/overview");
}
