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

const searchBar = document.getElementById("search-bar");
const searchResults = document.getElementById("search-results");

searchBar.addEventListener("keyup", function (event) {
  if (searchBar.value.length > 2) {
    fetch("/api/search?query=" + encodeURIComponent(searchBar.value))
      .then((response) => {
        if (response.status == 404) {
          console.log("No results found for search query");
          searchResults.innerHTML = "";
          searchResults.style.display = "block";
          const noResults = document.createElement("a");
          noResults.href = "#";
          noResults.innerHTML = "No results found for search query";
          searchResults.appendChild(noResults);
        } else {
          return response.json().then((data) => {
            searchResults.innerHTML = "";
            searchResults.style.display = "block";
            if (data.results.length === 0) {
              const noResults = document.createElement("a");
              noResults.href = "#";
              noResults.innerHTML = "No results found for search query";
              searchResults.appendChild(noResults);
            } else {
              data.results.forEach((element) => {
                console.log(element);
                const result = document.createElement("a");
                result.href = "/blog/" + element.blog_metadata.slug;  
                result.innerHTML = element.blog_metadata.title;
                searchResults.appendChild(result);
              });
            }
          });
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        searchResults.innerHTML = "";
        searchResults.style.display = "block";
        const errorMessage = document.createElement("a");
        errorMessage.href = "#";
        errorMessage.innerHTML = "An error occurred";
        searchResults.appendChild(errorMessage);
      });
  } else {
    searchResults.innerHTML = "";
    searchResults.style.display = "none";
  }
});

document.addEventListener("click", function (event) {
  if (!searchResults.contains(event.target) && event.target !== searchBar) {
    searchResults.style.display = "none";
  }
});

searchBar.addEventListener("focus", function () {
  if (searchBar.value.length > 2) {
    searchResults.style.display = "block";
  };
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
