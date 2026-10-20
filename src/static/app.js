document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const accountButton = document.getElementById("account-button");
  const authStatus = document.getElementById("auth-status");
  const loginDialog = document.getElementById("login-dialog");
  const loginForm = document.getElementById("login-form");
  const loginMessage = document.getElementById("login-message");
  let teacherAuthenticated = false;

  function showMessage(element, text, className) {
    element.textContent = text;
    element.className = className;
    element.classList.remove("hidden");
  }

  function createTextElement(tagName, text, className) {
    const element = document.createElement(tagName);
    element.textContent = text;
    if (className) {
      element.className = className;
    }
    return element;
  }

  function updateAuthUi(status) {
    teacherAuthenticated = status.authenticated;
    accountButton.textContent = teacherAuthenticated
      ? `👤 ${status.username} · Log out`
      : "👤 Teacher login";
    accountButton.setAttribute(
      "aria-label",
      teacherAuthenticated ? "Log out" : "Teacher login"
    );
    accountButton.disabled = !status.configured && !teacherAuthenticated;
    if (!status.configured && !teacherAuthenticated) {
      accountButton.textContent = "👤 Teacher login unavailable";
    }
    authStatus.textContent = teacherAuthenticated
      ? "Teacher mode: you can manage registrations."
      : status.configured
        ? "Student view: ask a teacher to sign in to manage registrations."
        : "Student view: teacher login is not configured.";
    signupForm.classList.toggle("hidden", !teacherAuthenticated);
  }

  async function fetchAuthStatus() {
    const response = await fetch("/auth/status");
    if (!response.ok) {
      throw new Error("Failed to check teacher login status");
    }
    updateAuthUi(await response.json());
  }

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";
      while (activitySelect.options.length > 1) {
        activitySelect.remove(1);
      }

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;

        activityCard.append(
          createTextElement("h4", name),
          createTextElement("p", details.description),
          createTextElement("p", `Schedule: ${details.schedule}`),
          createTextElement("p", `Availability: ${spotsLeft} spots left`)
        );

        const participantsContainer = document.createElement("div");
        participantsContainer.className = "participants-container";
        if (details.participants.length > 0) {
          const participantsSection = document.createElement("div");
          participantsSection.className = "participants-section";
          participantsSection.appendChild(createTextElement("h5", "Participants:"));
          const participantsList = document.createElement("ul");
          participantsList.className = "participants-list";

          details.participants.forEach((email) => {
            const participant = document.createElement("li");
            participant.appendChild(
              createTextElement("span", email, "participant-email")
            );
            if (teacherAuthenticated) {
              const deleteButton = createTextElement("button", "❌", "delete-btn");
              deleteButton.type = "button";
              deleteButton.dataset.activity = name;
              deleteButton.dataset.email = email;
              deleteButton.setAttribute(
                "aria-label",
                `Unregister ${email} from ${name}`
              );
              deleteButton.addEventListener("click", handleUnregister);
              participant.appendChild(deleteButton);
            }
            participantsList.appendChild(participant);
          });

          participantsSection.appendChild(participantsList);
          participantsContainer.appendChild(participantsSection);
        } else {
          participantsContainer.appendChild(
            createTextElement("p", "No participants yet")
          );
        }
        activityCard.appendChild(participantsContainer);

        activitiesList.appendChild(activityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    const button = event.target;
    const activity = button.dataset.activity;
    const email = button.dataset.email;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(messageDiv, result.message, "success");

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        showMessage(messageDiv, result.detail || "An error occurred", "error");
      }

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      showMessage(messageDiv, "Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
  }

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(messageDiv, result.message, "success");
        signupForm.reset();

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        showMessage(messageDiv, result.detail || "An error occurred", "error");
      }

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      showMessage(messageDiv, "Failed to sign up. Please try again.", "error");
      console.error("Error signing up:", error);
    }
  });

  accountButton.addEventListener("click", async () => {
    if (teacherAuthenticated) {
      try {
        const response = await fetch("/auth/logout", { method: "POST" });
        const result = await response.json();
        if (!response.ok) {
          throw new Error(result.detail || "Failed to log out");
        }
        updateAuthUi({ configured: true, authenticated: false });
        fetchActivities();
        showMessage(messageDiv, result.message, "success");
      } catch (error) {
        showMessage(messageDiv, error.message, "error");
      }
      return;
    }

    loginMessage.textContent = "";
    loginMessage.className = "hidden";
    loginDialog.showModal();
  });

  document.getElementById("cancel-login").addEventListener("click", () => {
    loginDialog.close();
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(loginForm);
    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: formData.get("username"),
          password: formData.get("password"),
        }),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Failed to log in");
      }

      loginForm.reset();
      loginDialog.close();
      await fetchAuthStatus();
      await fetchActivities();
      showMessage(messageDiv, result.message, "success");
    } catch (error) {
      showMessage(loginMessage, error.message, "error");
    }
  });

  async function initializeApp() {
    try {
      await fetchAuthStatus();
      await fetchActivities();
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to initialize the application. Please try again later.</p>";
      console.error("Error initializing app:", error);
    }
  }

  initializeApp();
});
