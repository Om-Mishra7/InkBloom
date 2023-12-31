function toggleDropdown() {
  if (document.getElementById("profile-dropdown").style.display == "none") {
    document.getElementById("profile-dropdown").style.display = "flex";

    document.addEventListener("click", function (event) {
      let profileDropdown = document.getElementById("profile-dropdown");
      if (event.target != profileDropdown && event.target != profilePic) {
        profileDropdown.style.display = "none";
      }
    });
  } else {
    document.getElementById("profile-dropdown").style.display = "none";
  }
}

let searchBar = document.getElementById("search-bar");

searchBar.addEventListener("keyup", function (event) {
  if (searchBar.value.length > 2) {
    fetch("/api/v1/search?query=" + searchBar.value)
      .then((response) => {
        if (response.status == 404) {
          console.log("No results found");
          let searchResults = document.getElementById("search-results");
          searchResults.innerHTML = "";
          searchResults.style.display = "block";
          let noResults = document.createElement("a");
          noResults.href = "#";
          noResults.innerHTML = "No results found";
          searchResults.appendChild(noResults);
          searchResults.addEventListener("mouseleave", function () {
            searchResults.style.display = "none";
          });
        } else {
          return response.json().then((data) => {
            let searchResults = document.getElementById("search-results");
            searchResults.innerHTML = "";
            searchResults.style.display = "block";
            data.forEach((element) => {
              let result = document.createElement("a");
              result.href = "/blogs/" + element.slug;
              result.innerHTML = element.title;
              searchResults.appendChild(result);
            });
            document.addEventListener("click", function (event) {
              let searchResults = document.getElementById("search-results");
              if (event.target != searchResults) {
                searchResults.style.display = "none";
              }
            });
          });
        }
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  } else {
    let searchResults = document.getElementById("search-results");
    searchResults.innerHTML = "";
    searchResults.style.display = "none";
  }
});

let profilePic = document.getElementById("profile-pic");
if (profilePic) {
  profilePic.addEventListener("click", function () {
    toggleDropdown();
  });
}

if (document.getElementById("profile-dropdown")) {
  document.getElementById("profile-dropdown").style.display = "none";
}
