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

// If there is a message in the URL, display it as an alert
let urlParams = new URLSearchParams(window.location.search);
let message = urlParams.get('message');

if (message) {
  createAlert("error", message);
}