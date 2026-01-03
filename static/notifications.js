// In-app Notification System for PeerNet++
class InAppNotificationManager {
  constructor() {
    this.container = null;
    this.notifications = [];
    this.maxNotifications = 5;

    // Ensure DOM is ready before initializing
    if (document.body) {
      this.init();
    } else {
      document.addEventListener("DOMContentLoaded", () => this.init());
    }
  }

  init() {
    // Create notification container
    this.container = document.createElement("div");
    this.container.id = "notification-container";
    this.container.style.cssText = `
      position: fixed;
      top: 80px;
      right: 20px;
      z-index: 9999;
      max-width: 400px;
      pointer-events: none;
    `;
    document.body.appendChild(this.container);
  }

  show(options) {
    const {
      title = "Notification",
      message = "",
      type = "info", // info, success, warning, error, processing
      duration = 5000,
      persistent = false,
    } = options;

    // Remove oldest if we have too many
    if (this.notifications.length >= this.maxNotifications) {
      this.removeNotification(this.notifications[0]);
    }

    const notification = this.createNotificationElement(
      title,
      message,
      type,
      persistent
    );
    this.container.appendChild(notification);
    this.notifications.push(notification);

    // Trigger animation
    setTimeout(() => {
      notification.style.transform = "translateX(0)";
      notification.style.opacity = "1";
    }, 10);

    // Auto-remove if not persistent
    if (!persistent && duration > 0) {
      setTimeout(() => {
        this.removeNotification(notification);
      }, duration);
    }

    return notification;
  }

  createNotificationElement(title, message, type, persistent) {
    const notification = document.createElement("div");
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
      background: white;
      border-radius: 1rem;
      padding: 1.25rem;
      margin-bottom: 1rem;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
      transform: translateX(450px);
      opacity: 0;
      transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
      pointer-events: all;
      border-left: 5px solid;
      max-width: 400px;
      animation: slideIn 0.4s ease;
    `;

    // Set border color based on type
    const colors = {
      info: "#0369a1",
      success: "#15803d",
      warning: "#c2410c",
      error: "#b91c1c",
      processing: "#1e3a8a",
    };
    notification.style.borderLeftColor = colors[type] || colors.info;

    // Icon based on type
    const icons = {
      info: "fa-info-circle",
      success: "fa-check-circle",
      warning: "fa-exclamation-triangle",
      error: "fa-times-circle",
      processing: "fa-spinner fa-spin",
    };
    const icon = icons[type] || icons.info;

    notification.innerHTML = `
      <div style="display: flex; align-items: flex-start; gap: 1rem;">
        <div style="flex-shrink: 0;">
          <i class="fas ${icon}" style="color: ${
      colors[type]
    }; font-size: 1.5rem;"></i>
        </div>
        <div style="flex: 1; min-width: 0;">
          <div style="font-weight: 700; font-size: 1rem; color: #0f172a; margin-bottom: 0.25rem;">
            ${title}
          </div>
          <div style="font-size: 0.875rem; color: #475569; line-height: 1.5;">
            ${message}
          </div>
        </div>
        ${
          !persistent
            ? `
          <button class="notification-close" style="
            background: none;
            border: none;
            cursor: pointer;
            color: #94a3b8;
            font-size: 1.25rem;
            padding: 0;
            line-height: 1;
            transition: color 0.2s;
            flex-shrink: 0;
          ">
            <i class="fas fa-times"></i>
          </button>
        `
            : ""
        }
      </div>
    `;

    // Close button handler
    if (!persistent) {
      const closeBtn = notification.querySelector(".notification-close");
      closeBtn.addEventListener("mouseenter", (e) => {
        e.target.style.color = "#ef4444";
      });
      closeBtn.addEventListener("mouseleave", (e) => {
        e.target.style.color = "#94a3b8";
      });
      closeBtn.addEventListener("click", () => {
        this.removeNotification(notification);
      });
    }

    return notification;
  }

  removeNotification(notification) {
    if (!notification || !notification.parentNode) return;

    notification.style.transform = "translateX(450px)";
    notification.style.opacity = "0";

    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
      const index = this.notifications.indexOf(notification);
      if (index > -1) {
        this.notifications.splice(index, 1);
      }
    }, 400);
  }

  updateNotification(notification, options) {
    const { title, message, type } = options;

    if (title || message) {
      const titleEl = notification.querySelector("div > div:first-child");
      const messageEl = notification.querySelector("div > div:last-child");

      if (title && titleEl) titleEl.textContent = title;
      if (message && messageEl) messageEl.textContent = message;
    }

    if (type) {
      const colors = {
        info: "#0369a1",
        success: "#15803d",
        warning: "#c2410c",
        error: "#b91c1c",
        processing: "#1e3a8a",
      };
      notification.style.borderLeftColor = colors[type] || colors.info;
    }
  }

  // Specific notification types
  showProcessing(paperId, title) {
    return this.show({
      title: "Processing Paper",
      message: `"${this.truncate(title, 50)}" is being processed...`,
      type: "processing",
      persistent: true,
    });
  }

  showReviewStarted(paperId, title) {
    return this.show({
      title: "Review Started",
      message: `AI reviewers are analyzing "${this.truncate(title, 50)}"`,
      type: "info",
      duration: 6000,
    });
  }

  showReviewProgress(paperId, message) {
    return this.show({
      title: "Review Progress",
      message: message,
      type: "info",
      duration: 4000,
    });
  }

  showReviewComplete(paperId, title, decision) {
    const typeMap = {
      Accept: "success",
      Reject: "error",
      "Minor Revision": "warning",
      "Major Revision": "warning",
      "Needs Revision": "warning",
    };

    return this.show({
      title: "Review Complete",
      message: `"${this.truncate(title, 40)}" - Decision: ${decision}`,
      type: typeMap[decision] || "info",
      duration: 8000,
    });
  }

  showUploadSuccess(title) {
    return this.show({
      title: "Upload Successful",
      message: `"${this.truncate(title, 50)}" has been uploaded successfully`,
      type: "success",
      duration: 5000,
    });
  }

  showUploadError(error) {
    return this.show({
      title: "Upload Failed",
      message: error || "An error occurred during upload",
      type: "error",
      duration: 7000,
    });
  }

  showBatchProgress(current, total) {
    return this.show({
      title: "Batch Upload Progress",
      message: `Processing ${current} of ${total} papers...`,
      type: "processing",
      persistent: true,
    });
  }

  showBatchComplete(successful, total) {
    return this.show({
      title: "Batch Upload Complete",
      message: `Successfully uploaded ${successful} of ${total} papers`,
      type: successful === total ? "success" : "warning",
      duration: 7000,
    });
  }

  truncate(str, maxLength) {
    if (!str) return "";
    return str.length > maxLength ? str.substring(0, maxLength) + "..." : str;
  }

  clearAll() {
    this.notifications.forEach((n) => this.removeNotification(n));
  }
}

// Initialize global notification manager
const inAppNotifications = new InAppNotificationManager();

// Make it globally accessible
window.inAppNotifications = inAppNotifications;
