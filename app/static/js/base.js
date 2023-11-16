function createAlert(type, message) {
  let errorContainer = document.getElementById("error-container");
  let errorMessage = document.getElementById("error-message");
    errorMessage.innerHTML = message.replace(/-/g, ' ');
    errorContainer.classList.add(`${type}`);
    errorContainer.style.display = "flex";

  setTimeout(() => {
    errorContainer.style.display = "none";
    errorContainer.classList.remove(`${type}`);
  }
    , 5000);
}