const unsubscribeButton = document.getElementById("unsubscribe-button");
const subscribeButton = document.getElementById("subscribe-button");
const userID = document.getElementById("user-id").getAttribute("data-user-id");
const exportButton = document.getElementById("export-button");
const deleteAccountButton = document.getElementById("delete-account-button");

const commentDeleteButtons = document.querySelectorAll(".delete-button");

commentDeleteButtons.forEach((button) => {
  button.addEventListener("click", deleteComment);
});

function deleteComment() {
  event.preventDefault();
  const commentID = this.getAttribute("data-comment-id");

  fetch(`/api/v1/user/comments/${commentID}`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ crsf_token: document.getElementById("csrf_token") }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.status === "success") {
        this.parentElement.parentElement.remove();
        createAlert("success", data.message);
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      createAlert("danger", data.message);
    });
}

if (userID === null || userID === undefined) {
  createAlert("danger", "An unexpected error occurred, please try again later");
}

if (unsubscribeButton) {
  unsubscribeButton.addEventListener("click", () => {
    event.preventDefault();
    fetch(`/api/v1/users/${userID}/unsubscribe`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ crsf_token: document.getElementById("csrf_token") }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.status === "success") {
          window.location.reload();
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        createAlert("danger", data.message);
      });
  });
}

if (subscribeButton) {
  subscribeButton.addEventListener("click", () => {
    event.preventDefault();
    fetch(`/api/v1/users/${userID}/subscribe`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ crsf_token: document.getElementById("csrf_token"), email: document.getElementById("email").value }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.status === "success") {
          window.location.reload();
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        createAlert("danger", data.message);
      });
  });
}

exportButton.addEventListener("click", () => {
  event.preventDefault();
  window.location.href = `/api/v1/users/${userID}/export`;
});

deleteAccountButton.addEventListener("click", () => {
  event.preventDefault();
  confirm(
    "Are you sure you want to delete your account, this action cannot be undone?"
  );
  fetch(`/api/v1/users/${userID}/delete`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ crsf_token: document.getElementById("csrf_token") }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.status === "success") {
        window.location.href = "/";
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      createAlert("danger", data.message);
    });
});
