function toggleDropdown() {
  if (document.getElementById("profile-dropdown").style.display == "none") {
    document.getElementById("profile-dropdown").style.display = "flex";

    document
      .getElementById("profile-dropdown")
      .addEventListener("mouseleave", function () {
        document.getElementById("profile-dropdown").style.display = "none";
      });
  } else {
    document.getElementById("profile-dropdown").style.display = "none";
  }
}
