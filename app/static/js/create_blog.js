tinymce.init({
  selector: "textarea#naked",
  skin: "naked",
  icons: "small",
  toolbar_location: "bottom",
  plugins: "lists code table codesample link autolink image imagetools media charmap hr anchor pagebreak nonbreaking preview searchreplace wordcount visualblocks visualchars fullscreen insertdatetime media table contextmenu paste help",
  toolbar:
    "blocks | bold italic underline strikethrough bullist link codesample | alignleft aligncenter alignright alignjustify | outdent indent | image media | forecolor backcolor | charmap emoticons | hr pagebreak | removeformat code | undo redo | fullscreen preview | help | insertfile image media template link anchor codesample | a11ycheck ltr rtl | showcomments addcomment | visualchars visualblocks nonbreaking table",
  menubar: false,
  images_upload_url: "/api/v1/user-content/upload",
  statusbar: false,
});

let newPostForm = document.getElementById("new-post-form");

newPostForm.addEventListener("submit", (e) => {
  e.preventDefault();
  let title = document.getElementById("title").value;
  let csrfToken = document.getElementById("csrf_token").value;
  let visibility = document.getElementById("visibility").value;
  console.log(visibility);
  let content = tinymce.get("naked").getContent();
  let tags = document.getElementById("tags").value;
  let summary = document.getElementById("summary").value;
  let coverImge = document.getElementById("file-input").files[0];

  
  let formData = new FormData();
  formData.append("title", title);
  formData.append("visibility", visibility);
  formData.append("content", content);
  formData.append("tags", tags);
  formData.append("summary", summary);
  formData.append("csrf_token", csrfToken);
  formData.append("cover_image", coverImge);

  fetch(window.location.pathname, {
    method: "POST",
    body: formData,
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.status == "success") {
        createAlert("success", data.message.replace(/\s/g , '-').trim());
        setTimeout(() => {
          window.location.href = "/blogs/" + data.blog_slug;
        }, 1000);
      } else {
        createAlert(data.message);
      }
    })
    .catch((err) => console.log(err));
});
