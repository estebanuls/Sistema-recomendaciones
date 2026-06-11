import { createRatingSelector } from "/components/RatingSelector.js";

export function createMovieCard(movie, { onLike, onRate } = {}) {
  const article = document.createElement("article");
  article.className = "movie-card";

  const genreMarkup = (movie.genres || [])
    .map((genre) => `<span class="chip">${genre}</span>`)
    .join("");

  article.innerHTML = `
    <div class="card-header">
      <h4><a href="/movie.html?id=${movie.id}" class="movie-link">${movie.title}</a></h4>
      <div class="genre-list">${genreMarkup || '<span class="chip">Sin genero</span>'}</div>
    </div>
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
    <p class="movie-explanation">${movie.explanation || "Usala para alimentar tu perfil de preferencias."}</p>
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
      onSubmit: (rating) => onRate?.(movie, rating),
    }),
  );

  article.querySelectorAll("[data-like]").forEach((button) => {
    button.addEventListener("click", () => {
      const liked = button.dataset.like === "true";
      onLike?.(movie, liked);
    });
  });

  return article;
}
