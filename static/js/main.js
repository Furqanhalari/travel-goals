document.addEventListener("DOMContentLoaded", function () {
  const userStr = localStorage.getItem("user");
  const nav = document.querySelector("#mainNav");

  const mobileBtn = document.getElementById("mobileMenuBtn");
  if (mobileBtn) {
    mobileBtn.addEventListener("click", function () {
      this.classList.toggle("active");
      nav.classList.toggle("active");
    });
  }

  if (userStr) {
    try {
      const user = JSON.parse(userStr);

      if (
        user.role === "customer" &&
        !document.querySelector('a[href="/my-requests"]')
      ) {
        const requestsLi = document.createElement("li");
        requestsLi.innerHTML =
          '<a href="/my-requests" class="header_link">My Requests</a>';

        const bookingLink = document.querySelector('a[href$="/contact"]');
        if (bookingLink && bookingLink.parentNode) {
          nav.insertBefore(requestsLi, bookingLink.parentNode);
        } else {
          nav.appendChild(requestsLi);
        }
      }

      if (user.role === "admin") {
        if (!document.querySelector('a[href="/admin"]')) {
          const adminLi = document.createElement("li");
          adminLi.innerHTML =
            '<a href="/admin" class="header_link">Admin Dashboard</a>';

          const homeLink = nav.querySelector("li");
          if (homeLink && homeLink.nextSibling) {
            nav.insertBefore(adminLi, homeLink.nextSibling);
          } else {
            nav.appendChild(adminLi);
          }
        }
      }

      if (!document.querySelector(".logout-btn")) {
        const logoutLi = document.createElement("li");
        logoutLi.innerHTML =
          '<a href="#" class="header_link logout-btn" onclick="handleLogout(event)">Logout</a>';
        nav.appendChild(logoutLi);
      }
    } catch (e) {
      console.error("Error parsing user data:", e);
    }
  }

  highlightActiveLink();
});

function highlightActiveLink() {
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll("nav ul a");

  navLinks.forEach((link) => {
    const href = link.getAttribute("href");
    if (href === currentPath || (currentPath === "/" && href === "/index")) {
      link.classList.add("active");
    }
  });
}

function handleLogout(event) {
  event.preventDefault();

  fetch("/api/logout", {
    method: "POST",
    credentials: "include",
  })
    .then((response) => {
      if (response.ok) {
        localStorage.removeItem("user");
        window.location.href = "/login";
      }
    })
    .catch((error) => {
      console.error("Logout error:", error);
    });
}
