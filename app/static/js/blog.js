function viewStats() {
  if (localStorage.getItem(window.location.pathname.replace("/blogs/", ""))) {
    const lastView = localStorage.getItem(window.location.pathname.replace("/blogs/", ""));
    if (new Date().getTime() - lastView < 60000) {
      setTimeout(() => {
        viewStats();
      }
        , 60000);
      return;
    }
  }
  localStorage.setItem(window.location.pathname.replace("/blogs/", ""), new Date().getTime());
  fetch(`/api/v1/statisics/views/${window.location.pathname.replace("/blogs/", "")}`, {
    method: "POST",
  })
    .then((response) => {
      if (response.status === 200) {
        return response.json();
      } else {
        throw new Error("Error");
      }
    })
    .catch((error) => {
      console.log(error);
      setTimeout(() => {
        viewStats();
      }
        , 60000);
    });
}

hljs.highlightAll(); // Ensure that the code blocks are still syntax highlighted

viewStats();

