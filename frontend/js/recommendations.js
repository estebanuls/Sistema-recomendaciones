import { createMovieCard } from "/components/MovieCard.js";
import {
  fetchRecommendations,
  likeMovie,
  rateMovie,
} from "/js/api.js";
import { logout, resolveActiveUser } from "/js/auth.js";

const state = {
  session: null,
  user: null,
  recommendations: [],
};

const elements = {
  recommendationsGrid: document.querySelector("#recommendations-grid"),
  welcomeTitle: document.querySelector("#welcome-title"),
  strategyPill: document.querySelector("#strategy-pill"),
  toast: document.querySelector("#toast"),
  logoutButton: document.querySelector("#logout-button"),
  refreshRecommendations: document.querySelector("#refresh-recommendations"),
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

async function handleLike(movie, liked) {
  await likeMovie(state.session.access_token, movie.id, liked);
  showToast(liked ? `Guardaste "${movie.title}" como favorita.` : `Marcaste "${movie.title}" como no favorita.`);
  await loadRecommendations();
}

async function handleRate(movie, rating) {
  await rateMovie(state.session.access_token, movie.id, rating);
  showToast(`Guardaste ${rating} para "${movie.title}".`);
  await loadRecommendations();
}

function renderMovieCollection(container, items) {
  container.replaceChildren();
  if (!items.length) {
    const emptyState = document.createElement("p");
    emptyState.className = "meta-text";
    emptyState.textContent = "No hay resultados para mostrar todavia.";
    container.appendChild(emptyState);
    return;
  }
  items.forEach((movie) => {
    container.appendChild(
      createMovieCard(movie, {
        onLike: handleLike,
        onRate: handleRate,
      }),
    );
  });
}

function resolveStrategyLabel(strategy) {
  return strategy === "catalog-popularity" ? "Mas populares" : "Recomendadas para ti";
}

async function loadRecommendations() {
  const response = await fetchRecommendations(state.session.access_token);
  state.recommendations = response.items;
  elements.strategyPill.textContent = resolveStrategyLabel(response.strategy);
  renderMovieCollection(elements.recommendationsGrid, response.items);
}

async function refreshRecommendations() {
  if (!elements.refreshRecommendations) {
    return;
  }

  const originalLabel = elements.refreshRecommendations.textContent;
  elements.refreshRecommendations.disabled = true;
  elements.refreshRecommendations.textContent = "Actualizando...";
  try {
    await loadRecommendations();
    showToast("Recomendaciones actualizadas.");
  } finally {
    elements.refreshRecommendations.disabled = false;
    elements.refreshRecommendations.textContent = originalLabel;
  }
}

async function bootstrap() {
  const activeUser = await resolveActiveUser();
  state.session = activeUser.session;
  state.user = activeUser.user;

  elements.welcomeTitle.textContent = `Hola, ${state.user.display_name}.`;

  elements.logoutButton?.addEventListener("click", logout);
  elements.refreshRecommendations?.addEventListener("click", refreshRecommendations);

  await loadRecommendations();
}

bootstrap().catch((error) => {
  console.error(error);
  showToast(error.message);
});
