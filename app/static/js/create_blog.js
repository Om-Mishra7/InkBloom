tinymce.init({
  selector: "textarea#naked",
  skin: "naked",
  icons: "small",
  toolbar_location: "bottom",
  plugins: "lists code table codesample link autolink image imagetools media charmap hr anchor pagebreak nonbreaking",
  toolbar:
    "blocks | bold italic underline strikethrough bullist link codesample | alignleft aligncenter alignright alignjustify | outdent indent | image media | forecolor backcolor | charmap emoticons | hr pagebreak | removeformat code | undo redo | fullscreen",
  menubar: false,
  images_upload_url: "/api/v1/user-content/upload",
  statusbar: false,
});

let newPostForm = document.getElementById("new-post-form");

newPostForm.addEventListener("submit", (e) => {
  e.preventDefault();
  let title = document.getElementById("title").value;
  let category = document.getElementById("category").value;
  let content = tinymce.get("naked").getContent();
  let tags = document.getElementById("tags").value;
  let summary = document.getElementById("summary").value;
  let coverImge = document.getElementById("file-input").files[0];

  
  let formData = new FormData();
  formData.append("title", title);
  formData.append("category", category);
  formData.append("content", content);
  formData.append("tags", tags);
  formData.append("summary", summary);
  formData.append("cover_image", coverImge);

  fetch("/admin/blogs/create", {
    method: "POST",
    body: formData,
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.status == "success") {
        window.location.href = "/blogs/" + data.blog_slug;
      } else {
        alert(data.message);
      }
    })
    .catch((err) => console.log(err));
});
