import { fetchProfile } from "/js/api.js";
import { logout, resolveActiveUser } from "/js/auth.js";

const elements = {
  title: document.querySelector("#profile-title"),
  stats: document.querySelector("#profile-stats"),
  genres: document.querySelector("#favorite-genres"),
  history: document.querySelector("#profile-history"),
  logout: document.querySelector("#profile-logout"),
};

function renderStats(profile) {
  const boxes = [
    { label: "Likes", value: profile.liked_count },
    { label: "Ratings", value: profile.rated_count },
    { label: "Historial", value: profile.history_count },
    { label: "Usuario", value: profile.user.username },
  ];

  elements.stats.replaceChildren(
    ...boxes.map((entry) => {
      const article = document.createElement("article");
      article.className = "stat-box";
      article.innerHTML = `<span>${entry.label}</span><strong>${entry.value}</strong>`;
      return article;
    }),
  );
}

function renderGenres(genres) {
  elements.genres.replaceChildren();
  if (!genres.length) {
    const text = document.createElement("p");
    text.className = "meta-text";
    text.textContent = "Todavía no hay suficiente señal positiva para detectar géneros fuertes.";
    elements.genres.appendChild(text);
    return;
  }

  genres.forEach((genre) => {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = genre;
    elements.genres.appendChild(chip);
  });
}

function renderHistory(items) {
  elements.history.replaceChildren();
  if (!items.length) {
    const empty = document.createElement("p");
    empty.className = "meta-text";
    empty.textContent = "Sin historial reciente.";
    elements.history.appendChild(empty);
    return;
  }

  items.forEach((item) => {
    const row = document.createElement("article");
    row.className = "history-item";
    row.innerHTML = `
      <div class="history-summary">
        <h4>${item.movie_title}</h4>
        <p class="meta-text">${(item.movie_genres || []).join(" · ") || "Sin géneros"}</p>
      </div>
      <div class="history-values">
        <strong>${item.rating ?? "Sin rating"}</strong>
        <span>${item.liked === null ? "Sin like" : item.liked ? "Te gustó" : "No te gustó"}</span>
      </div>
    `;
    elements.history.appendChild(row);
  });
}

async function bootstrap() {
  const activeUser = await resolveActiveUser();
  elements.title.textContent = activeUser.user.display_name;
  elements.logout?.addEventListener("click", logout);

  const profile = await fetchProfile(activeUser.session.access_token);
  renderStats(profile);
  renderGenres(profile.favorite_genres);
  renderHistory(profile.recent_history);
}

bootstrap().catch((error) => {
  console.error(error);
  window.location.href = "/login.html";
});
