import { createMovieCard } from "/components/MovieCard.js";
import {
  fetchCurrentUser,
  fetchMovies,
  likeMovie,
  rateMovie,
} from "/js/api.js";
import { getSession, logout } from "/js/auth.js";

const state = {
  query: "",
  session: null,
  user: null,
};

const elements = {
  title: document.querySelector("#search-title"),
  grid: document.querySelector("#search-results-grid"),
  toast: document.querySelector("#toast"),
  searchForm: document.querySelector("#navbar-search-form"),
  logoutButton: document.querySelector("#page-logout"),
};

function showToast(message) {
  if (!elements.toast) {
    return;
  }
  elements.toast.textContent = message;
  elements.toast.classList.add("visible");
  window.clearTimeout(showToast.timerId);
  showToast.timerId = window.setTimeout(() => {
    elements.toast.classList.remove("visible");
  }, 2200);
}

function renderMessage(message) {
  elements.grid.replaceChildren();
  const text = document.createElement("p");
  text.className = "meta-text";
  text.textContent = message;
  elements.grid.appendChild(text);
}

async function resolveOptionalUser() {
  const session = getSession();
  if (!session?.access_token) {
    return { session: null, user: null };
  }

  try {
    const response = await fetchCurrentUser(session.access_token);
    return { session, user: response.user };
  } catch {
    return { session: null, user: null };
  }
}

function requireInteractionSession() {
  if (state.session?.access_token) {
    return true;
  }
  showToast("Inicia sesion para guardar likes y ratings.");
  return false;
}

async function handleLike(movie, liked) {
  if (!requireInteractionSession()) {
    return;
  }
  await likeMovie(state.session.access_token, movie.id, liked);
  showToast(liked ? `Guardaste "${movie.title}" como favorita.` : `Marcaste "${movie.title}" como no favorita.`);
}

async function handleRate(movie, rating) {
  if (!requireInteractionSession()) {
    return;
  }
  await rateMovie(state.session.access_token, movie.id, rating);
  showToast(`Guardaste ${rating} para "${movie.title}".`);
}

function renderResults(items) {
  elements.grid.replaceChildren();
  items.forEach((movie) => {
    elements.grid.appendChild(
      createMovieCard(movie, {
        onLike: handleLike,
        onRate: handleRate,
      }),
    );
  });
}

async function bootstrap() {
  const searchParams = new URLSearchParams(window.location.search);
  state.query = searchParams.get("q")?.trim() ?? "";

  const input = elements.searchForm?.querySelector('input[name="q"]');
  if (input) {
    input.value = state.query;
  }

  elements.logoutButton?.addEventListener("click", logout);

  const activeUser = await resolveOptionalUser();
  state.session = activeUser.session;
  state.user = activeUser.user;

  if (!state.query) {
    elements.title.textContent = "Ingresa un termino de busqueda.";
    renderMessage("Ingresa un termino de busqueda.");
    return;
  }

  const response = await fetchMovies(state.query, 24);
  elements.title.textContent = `Resultados para "${state.query}" (${response.count} peliculas)`;

  if (!response.items.length) {
    renderMessage(`No se encontraron peliculas para "${state.query}".`);
    return;
  }

  renderResults(response.items);
}

bootstrap().catch((error) => {
  console.error(error);
  showToast(error.message);
  renderMessage("No fue posible cargar los resultados.");
});
