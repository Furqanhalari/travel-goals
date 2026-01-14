class ChatWidget {
  constructor() {
    this.isOpen = false;
    this.messages = [];
    this.conversationHistory = [];
    this.isLoading = false;
    this.init();
  }

  /**
   * Initialize the chat widget
   */
  init() {
    this.widget = document.getElementById("chat-widget");
    this.messagesContainer = document.getElementById("chat-messages");
    this.input = document.getElementById("chat-input");
    this.sendBtn = document.getElementById("chat-send");
    this.fab = document.getElementById("chat-fab");
    this.closeBtn = document.getElementById("chat-close");

    if (!this.widget || !this.fab) {
      console.error("Chatbot: Required elements not found");
      return;
    }

    this.fab.addEventListener("click", () => this.toggleWidget());
    this.closeBtn.addEventListener("click", () => this.toggleWidget());
    this.sendBtn.addEventListener("click", () => this.sendMessage());

    this.input.addEventListener("keypress", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    this.loadConversation();

    if (this.messages.length === 0) {
      this.addBotMessage(
        "Hi! 👋 I'm your AI travel assistant. Ask me about destinations, packages, or help with booking!"
      );
      this.loadQuickReplies();
    }

    console.log("Chatbot initialized successfully");
  }

  /**
   * Toggle the chat widget open/closed
   */
  toggleWidget() {
    this.isOpen = !this.isOpen;

    if (this.isOpen) {
      this.widget.classList.remove("hidden");
      this.input.focus();

      this.scrollToBottom();
    } else {
      this.widget.classList.add("hidden");
    }
  }

  /**
   * Send user message to the chatbot API
   */
  async sendMessage() {
    const message = this.input.value.trim();

    if (!message || this.isLoading) return;

    this.input.value = "";

    this.addUserMessage(message);

    this.conversationHistory.push({
      role: "user",
      content: message,
    });

    this.showTypingIndicator();
    this.isLoading = true;
    this.sendBtn.disabled = true;

    try {
      const isBookingQuery = this.detectBookingIntent(message);

      if (isBookingQuery) {
        const response = await fetch("/api/ai/booking-assistant", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: message }),
        });

        const data = await response.json();
        this.hideTypingIndicator();

        if (data.success) {
          this.addBotMessage(data.summary);

          if (data.packages && data.packages.length > 0) {
            this.displayPackageResults(data.packages);
          } else {
            this.addBotMessage(
              "I couldn't find any exact matches for those criteria. Try searching for a broader destination or budget!"
            );
          }
        } else {
          this.addBotMessage(
            data.message ||
              "I had trouble understanding that search. Try something like 'Book a 5-day beach trip'."
          );
        }
      } else {
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          credentials: "include",
          body: JSON.stringify({
            message: message,
            history: this.conversationHistory.slice(-10),
          }),
        });

        const data = await response.json();
        this.hideTypingIndicator();

        if (data.success) {
          this.addBotMessage(data.message);

          this.conversationHistory.push({
            role: "assistant",
            content: data.message,
          });

          this.loadQuickReplies(message);
        } else {
          this.addBotMessage(
            data.message || "Sorry, I encountered an error. Please try again."
          );
        }
      }
    } catch (error) {
      console.error("Chatbot error:", error);
      this.hideTypingIndicator();
      this.addBotMessage(
        "Sorry, I'm having connection issues. Please try again in a moment."
      );
    } finally {
      this.isLoading = false;
      this.sendBtn.disabled = false;
      this.input.focus();
      this.saveConversation();
    }
  }

  /**
   * Detect if a message looks like a booking or travel search request
   */
  detectBookingIntent(message) {
    const bookingKeywords = [
      "book",
      "booking",
      "reserve",
      "find",
      "search",
      "looking for",
      "want to go",
      "trip",
      "vacation",
      "travel to",
      "visit",
      "package for",
      "budget",
    ];

    const lowerMessage = message.toLowerCase();

    const hasKeyword = bookingKeywords.some((keyword) =>
      lowerMessage.includes(keyword)
    );

    const hasLogistics = /\d+\s*(days?|nights?|people|persons?|adults?)/.test(
      lowerMessage
    );

    return hasKeyword || hasLogistics;
  }

  /**
   * Display mini package cards inside the chat bubble
   */
  displayPackageResults(packages) {
    const resultsDiv = document.createElement("div");
    resultsDiv.className = "message bot";

    let resultsHTML = `
            <div class="message-bubble results-bubble">
                <div class="package-results">
                    <div class="results-header">📦 Top Matches for You</div>
        `;

    packages.slice(0, 3).forEach((pkg) => {
      resultsHTML += `
                <div class="package-card-mini">
                    <div class="pkg-header">
                        <strong>${this.escapeHtml(pkg.package_name)}</strong>
                        <span class="pkg-price">$${pkg.price}</span>
                    </div>
                    <div class="pkg-details">
                        📍 ${this.escapeHtml(
                          pkg.destination_name
                        )}, ${this.escapeHtml(pkg.destination_country)}<br>
                        ⏱️ ${pkg.duration} days
                    </div>
                    <div class="pkg-actions">
                        <a href="/packages?package_id=${
                          pkg.package_id
                        }" class="btn-view-mini">View Details →</a>
                    </div>
                </div>
            `;
    });

    if (packages.length > 3) {
      resultsHTML += `
                <div class="more-results">
                    + ${packages.length - 3} more matching packages
                </div>
            `;
    }

    resultsHTML += `
                </div>
                <div class="message-time">${this.getCurrentTime()}</div>
            </div>
        `;

    resultsDiv.innerHTML = resultsHTML;
    this.messagesContainer.appendChild(resultsDiv);

    this.messages.push({
      role: "bot",
      content: `[Package Results: ${packages.length} found]`,
    });

    this.scrollToBottom();
  }

  /**
   * Add a user message to the chat
   */
  addUserMessage(text) {
    const messageDiv = document.createElement("div");
    messageDiv.className = "message user";
    messageDiv.innerHTML = `
            <div class="message-bubble">
                ${this.escapeHtml(text)}
                <div class="message-time">${this.getCurrentTime()}</div>
            </div>
        `;

    this.messagesContainer.appendChild(messageDiv);
    this.messages.push({ role: "user", content: text });
    this.scrollToBottom();
  }

  /**
   * Add a bot message to the chat
   */
  addBotMessage(text) {
    const messageDiv = document.createElement("div");
    messageDiv.className = "message bot";

    const formattedText = this.formatBotMessage(text);

    messageDiv.innerHTML = `
            <div class="message-bubble">
                ${formattedText}
                <div class="message-time">${this.getCurrentTime()}</div>
            </div>
        `;

    this.messagesContainer.appendChild(messageDiv);
    this.messages.push({ role: "bot", content: text });
    this.scrollToBottom();
  }

  /**
   * Format bot message text
   */
  formatBotMessage(text) {
    let formatted = this.escapeHtml(text);

    formatted = formatted.replace(/\n/g, "<br>");

    formatted = formatted.replace(
      /(https?:\/\/[^\s]+)/g,
      '<a href="$1" target="_blank" rel="noopener">$1</a>'
    );

    return formatted;
  }

  /**
   * Show typing indicator
   */
  showTypingIndicator() {
    this.hideTypingIndicator();

    const typingDiv = document.createElement("div");
    typingDiv.className = "message bot";
    typingDiv.id = "typing-indicator";
    typingDiv.innerHTML = `
            <div class="message-bubble">
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;

    this.messagesContainer.appendChild(typingDiv);
    this.scrollToBottom();
  }

  /**
   * Hide typing indicator
   */
  hideTypingIndicator() {
    const typingDiv = document.getElementById("typing-indicator");
    if (typingDiv) {
      typingDiv.remove();
    }
  }

  /**
   * Load quick reply suggestions
   */
  async loadQuickReplies(context = "") {
    try {
      const response = await fetch(
        `/api/chat/suggestions?context=${encodeURIComponent(context)}`,
        {
          credentials: "include",
        }
      );
      const data = await response.json();

      if (data.success && data.suggestions) {
        this.showQuickReplies(data.suggestions);
      }
    } catch (error) {
      this.showQuickReplies([
        "🏖️ Beach destinations",
        "✈️ How to book?",
        "💰 Budget options",
        "📦 Popular packages",
      ]);
    }
  }

  /**
   * Display quick reply buttons
   */
  showQuickReplies(suggestions) {
    const existingReplies = document.querySelector(".quick-replies");
    if (existingReplies) {
      existingReplies.remove();
    }

    const repliesDiv = document.createElement("div");
    repliesDiv.className = "quick-replies";

    suggestions.slice(0, 4).forEach((suggestion) => {
      const btn = document.createElement("button");
      btn.className = "quick-reply-btn";
      btn.textContent = suggestion;
      btn.addEventListener("click", () => {
        this.input.value = suggestion;
        this.sendMessage();
        repliesDiv.remove();
      });
      repliesDiv.appendChild(btn);
    });

    this.messagesContainer.appendChild(repliesDiv);
    this.scrollToBottom();
  }

  /**
   * Scroll to the bottom of the messages container
   */
  scrollToBottom() {
    setTimeout(() => {
      this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }, 100);
  }

  /**
   * Get current time for message timestamps
   */
  getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  /**
   * Escape HTML to prevent XSS
   */
  escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Save conversation to session storage
   */
  saveConversation() {
    try {
      sessionStorage.setItem(
        "chatbot_messages",
        JSON.stringify(this.messages.slice(-50))
      );
      sessionStorage.setItem(
        "chatbot_history",
        JSON.stringify(this.conversationHistory.slice(-20))
      );
    } catch (e) {
      console.warn("Could not save chat history:", e);
    }
  }

  /**
   * Load conversation from session storage
   */
  loadConversation() {
    try {
      const savedMessages = sessionStorage.getItem("chatbot_messages");
      const savedHistory = sessionStorage.getItem("chatbot_history");

      if (savedHistory) {
        this.conversationHistory = JSON.parse(savedHistory);
      }

      if (savedMessages) {
        const messages = JSON.parse(savedMessages);
        messages.forEach((msg) => {
          if (msg.role === "user") {
            this.addUserMessage(msg.content);
          } else {
            this.addBotMessage(msg.content);
          }
        });
      }
    } catch (e) {
      console.warn("Could not load chat history:", e);
    }
  }

  /**
   * Clear conversation history
   */
  clearConversation() {
    this.messages = [];
    this.conversationHistory = [];
    this.messagesContainer.innerHTML = "";
    sessionStorage.removeItem("chatbot_messages");
    sessionStorage.removeItem("chatbot_history");

    this.addBotMessage(
      "Chat cleared! 👋 How can I help you with your travel plans?"
    );
    this.loadQuickReplies();
  }
}

document.addEventListener("DOMContentLoaded", () => {
  setTimeout(() => {
    window.chatWidget = new ChatWidget();
  }, 100);
});
