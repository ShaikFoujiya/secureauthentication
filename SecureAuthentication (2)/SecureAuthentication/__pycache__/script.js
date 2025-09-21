const faceAuthApp = {
    showView: function(viewId) {
        document.querySelectorAll(".view-container").forEach(v => v.style.display = "none");
        document.getElementById(viewId + "View").style.display = "block";
    },

    startCamera: function(videoId, captureBtnId, canvasId) {
        const video = document.getElementById(videoId);
        const canvas = document.getElementById(canvasId);
        const captureBtn = document.getElementById(captureBtnId);

        navigator.mediaDevices.getUserMedia({ video: true })
            .then(stream => {
                video.srcObject = stream;
                video.style.display = "block";
                captureBtn.style.display = "inline-block";
            })
            .catch(err => console.error("Camera error:", err));

        captureBtn.onclick = () => {
            const context = canvas.getContext("2d");
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
        };
    },

    registerUser: function() {
        const form = document.getElementById("registerForm");
        form.addEventListener("submit", async function(e) {
            e.preventDefault();

            const formData = new FormData();
            formData.append("username", document.getElementById("username").value);
            formData.append("email", document.getElementById("email").value);
            formData.append("password", document.getElementById("password").value);

            const canvas = document.getElementById("canvas");
            if (canvas.width === 0 || canvas.height === 0) {
                alert("Please capture your face!");
                return;
            }

            canvas.toBlob(blob => {
                formData.append("img", blob, "face.jpg");

                fetch("http://127.0.0.1:5000/api/register", {
                    method: "POST",
                    body: formData
                })
                .then(res => res.json())
                .then(data => {
                    if (data.error) alert("Error: " + data.error);
                    else alert("Success: " + data.message);
                })
                .catch(err => console.error(err));
            }, "image/jpeg");
        });
    },

    loginUser: function() {
        const form = document.getElementById("loginForm");
        form.addEventListener("submit", async function(e) {
            e.preventDefault();

            const formData = new FormData();
            formData.append("email", document.getElementById("loginEmail").value);
            formData.append("password", document.getElementById("loginPassword").value);

            const canvas = document.getElementById("canvas"); // capture face for login
            if (canvas.width > 0 && canvas.height > 0) {
                canvas.toBlob(blob => {
                    formData.append("img", blob, "face.jpg");
                    sendLogin(formData);
                }, "image/jpeg");
            } else {
                sendLogin(formData);
            }

            function sendLogin(data) {
                fetch("http://127.0.0.1:5000/api/login", {
                    method: "POST",
                    body: data
                })
                .then(res => res.json())
                .then(data => {
                    if (data.error) alert("Error: " + data.error);
                    else {
                        alert("Success: " + data.message);
                        faceAuthApp.showView("dashboard"); // show dashboard
                    }
                })
                .catch(err => console.error(err));
            }
        });
    },

    init: function() {
        // Show login by default
        this.showView("login");

        // Start cameras
        document.getElementById("startCamera").onclick = () =>
            this.startCamera("video", "captureBtn", "canvas");

        document.getElementById("startCameraLogin").onclick = () =>
            this.startCamera("videoLogin", "captureBtn", "canvas");

        // Register & login
        this.registerUser();
        this.loginUser();
    }
};

// Initialize app
window.onload = () => faceAuthApp.init();
