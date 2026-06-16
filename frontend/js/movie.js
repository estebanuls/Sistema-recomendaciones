import { createRatingSelector } from "/components/RatingSelector.js";
import { createMovieCard } from "/components/MovieCard.js";
import {
  fetchCurrentUser,
  fetchMovie,
  fetchMovies,
  likeMovie,
  rateMovie,
} from "/js/api.js";
import { getSession, logout } from "/js/auth.js";

const state = {
  movie: null,
  session: null,
  user: null,
};

const elements = {
  detail: document.querySelector("#movie-detail"),
  similarGrid: document.querySelector("#similar-movies-grid"),
  toast: document.querySelector("#toast"),
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

function renderSimilarMessage(message) {
  elements.similarGrid.replaceChildren();
  const text = document.createElement("p");
  text.className = "meta-text";
  text.textContent = message;
  elements.similarGrid.appendChild(text);
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

function renderMovieDetail(movie) {
  const genres = (movie.genres || [])
    .map((genre) => `<span class="chip">${genre}</span>`)
    .join("");

  const article = document.createElement("article");
  article.className = "movie-detail-card";
  article.innerHTML = `
    <p class="eyebrow">Ficha</p>
    <h2>${movie.title}</h2>
    <div class="genre-list">${genres || '<span class="chip">Sin genero</span>'}</div>
    <div class="meta-grid">
      <div class="meta-item">
        <span>Media historica</span>
        <strong>${Number(movie.mean_rating || 0).toFixed(2)}</strong>
      </div>
      <div class="meta-item">
        <span>Ratings</span>
        <strong>${movie.rating_count ?? 0}</strong>
      </div>
    </div>
    <p class="movie-explanation">Usa likes y ratings para reforzar tu perfil y descubrir peliculas parecidas.</p>
    <div class="card-actions">
      <div class="action-row">
        <button class="button small secondary" type="button" data-like="true">Me gusta</button>
        <button class="button small ghost" type="button" data-like="false">No me gusta</button>
      </div>
    </div>
  `;

  const actions = article.querySelector(".card-actions");
  actions.appendChild(
    createRatingSelector({
      onSubmit: (rating) => handleRate(movie, rating),
    }),
  );

  article.querySelectorAll("[data-like]").forEach((button) => {
    button.addEventListener("click", () => {
      const liked = button.dataset.like === "true";
      handleLike(movie, liked);
    });
  });

  elements.detail.replaceChildren(article);
}

function renderSimilarMovies(items) {
  elements.similarGrid.replaceChildren();
  items.forEach((movie) => {
    elements.similarGrid.appendChild(
      createMovieCard(movie, {
        onLike: handleLike,
        onRate: handleRate,
      }),
    );
  });
}

async function loadSimilarMovies(movie) {
  const firstGenre = movie.genres?.[0];
  if (!firstGenre) {
    renderSimilarMessage("No hay un genero principal disponible para buscar similares.");
    return;
  }

  const response = await fetchMovies(firstGenre, 8);
  const items = response.items.filter((candidate) => candidate.id !== movie.id);

  if (!items.length) {
    renderSimilarMessage(`No se encontraron peliculas similares para "${movie.title}".`);
    return;
  }

  renderSimilarMovies(items);
}

async function bootstrap() {
  elements.logoutButton?.addEventListener("click", logout);

  const activeUser = await resolveOptionalUser();
  state.session = activeUser.session;
  state.user = activeUser.user;

  const searchParams = new URLSearchParams(window.location.search);
  const movieId = searchParams.get("id");
  if (!movieId) {
    elements.detail.innerHTML = '<p class="meta-text">Debes indicar un id de pelicula valido.</p>';
    renderSimilarMessage("No hay peliculas similares para mostrar.");
    return;
  }

  const movie = await fetchMovie(movieId);
  state.movie = movie;
  document.title = `${movie.title} | MovieLens Recommender`;

  renderMovieDetail(movie);
  await loadSimilarMovies(movie);
}

bootstrap().catch((error) => {
  console.error(error);
  showToast(error.message);
  elements.detail.innerHTML = '<p class="meta-text">No fue posible cargar la pelicula solicitada.</p>';
  renderSimilarMessage("No fue posible cargar peliculas similares.");
});
