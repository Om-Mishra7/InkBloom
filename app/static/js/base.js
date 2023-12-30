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

function autoLogin() {
  fetch("/api/v1/user", {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      if (response.status === 200) {
        return;
      } else if (response.status === 401) {
        fetch("https://accounts.projectrexa.dedyn.io", {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
          },
        })
          .then((response) => {
            if (response.status === 200) {
              window.location.href = "/user/authorize/projectrexa";
            }
          })
          .catch((error) => {
            createAlert("error", "ProjectRexa authentication services are momentarily unavailable, auto-login has been disabled.");
          });
      }
    })
    .catch((error) => {
      createAlert("error", "ProjectRexa authentication services are momentarily unavailable, auto-login has been disabled.");
    });
}



document.addEventListener("DOMContentLoaded", () => {
  autoLogin();
});
