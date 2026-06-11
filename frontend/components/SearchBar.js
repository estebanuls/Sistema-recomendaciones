export function createSearchBar({ onSearch } = {}) {
  const form = document.createElement("form");
  form.className = "searchbar";
  form.innerHTML = `
    <input
      class="search-input"
      type="search"
      name="query"
      placeholder="Busca por título o género, por ejemplo: sci-fi, drama, pixar..."
      aria-label="Buscar película"
    >
    <button class="button" type="submit">Buscar</button>
  `;

  const input = form.querySelector("input");
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    onSearch?.(input.value.trim());
  });

  return form;
}
