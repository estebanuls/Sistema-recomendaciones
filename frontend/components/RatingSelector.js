const RATING_OPTIONS = [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5];

export function createRatingSelector({ onSubmit } = {}) {
  const wrapper = document.createElement("div");
  wrapper.className = "rating-control";

  const select = document.createElement("select");
  select.className = "rating-select";
  RATING_OPTIONS.forEach((value) => {
    const option = document.createElement("option");
    option.value = String(value);
    option.textContent = `${value.toFixed(1)} / 5`;
    if (value === 4) {
      option.selected = true;
    }
    select.appendChild(option);
  });

  const button = document.createElement("button");
  button.type = "button";
  button.className = "button small";
  button.textContent = "Guardar rating";
  button.addEventListener("click", () => {
    onSubmit?.(Number(select.value));
  });

  wrapper.append(select, button);
  return wrapper;
}
