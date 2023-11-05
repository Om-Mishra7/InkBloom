function viewStats() {
  fetch(`/api/v1/statisics/views${window.location.pathname.replace("/blogs", "")}`, {
    method: "POST",
  })
    .then((response) => {
      if (response.status === 200) {
        return response.json();
      } else {
        throw new Error("Error");
      }
    })
    .then((data) => {
      console.log(data);
    })
    .catch((error) => {
      console.log(error);
      setTimeout(() => {
        viewStats();
      }
        , 60000);
    });
}

viewStats();
console.log("Hello World");
