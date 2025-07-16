const app = createApp({
  setup() {
    // State:
    const isSidebarOpen = ref(window.innerWidth > 768);
    const hamburgerVisible = ref(!isSidebarOpen.value);
    const newMessage = ref("");
    const chatMessagesContainer = ref(null);
    const chatModels = ref(sidebarMenuChoices); // NOTE: sidebarMenuChoices is received from Django view.
    const currentModel = ref(chatModels.value[0]?.subItems[0]);
    const messages = ref([{ sender: "bot", text: "Hello! How can I help you today?" }]);
    const currentConfigValues = ref({});
    const isConfigModalVisible = ref(false);

    // Method:
    const toggleSidebar = () => {
      if (isSidebarOpen.value) {
        isSidebarOpen.value = false;
        setTimeout(() => {
          hamburgerVisible.value = true;
        }, 150);
      } else {
        hamburgerVisible.value = false;
        isSidebarOpen.value = true;
      }
    };

    const resetChat = () => {
      messages.value = [
        {
          sender: "bot",
          text: `Switched to ${currentModel.value.name}. Ask me anything!`,
        },
      ];
    };

    const handleCategoryClick = (category) => {
      // Expand/Close if has subItems, otherwise select.
      if (category.subItems && category.subItems.length > 0) {
        category.isExpanded = !category.isExpanded;
      } else {
        selectModel(category);
      }
    };

    const isCategoryActive = (category) => {
      if (category.apiUrl === currentModel.value.apiUrl) {
        return true;
      }
      if (category.subItems) {
        return category.subItems.some((sub) => sub.apiUrl === currentModel.value.apiUrl);
      }
      return false;
    };

    const selectModel = (model) => {
      currentModel.value = model;
      resetChat();
      currentConfigValues.value = {};

      // Set New Configuration Options
      if (model.configOptions) {
        model.configOptions.forEach((config) => {
          currentConfigValues.value[config.key] = config.defaultValue;
        });
      }

      if (window.innerWidth < 768 && isSidebarOpen.value) {
        toggleSidebar();
      }
    };

    const scrollToBottom = async () => {
      await nextTick();
      const container = chatMessagesContainer.value;
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    };

    const sendMessage = async () => {
      const userInput = newMessage.value.trim();
      if (!userInput) return;

      messages.value.push({ sender: "user", text: userInput });
      newMessage.value = "";
      await scrollToBottom();

      try {
        const response = await fetch(currentModel.value.apiUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken"),
          },
          body: JSON.stringify({ message: userInput, ...currentConfigValues.value }),
        });
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        if (data.message) {
          const sanitizedHtml = DOMPurify.sanitize(data.message);
          messages.value.push({ sender: "bot", text: sanitizedHtml });
        } else {
          throw new Error(data.error || "Unknown API error");
        }
      } catch (error) {
        console.error("Fetch Error:", error);
        messages.value.push({
          sender: "bot",
          text: "Sorry, I couldn't connect to the server.",
        });
      }
      await scrollToBottom();
    };

    const toggleConfigModal = () => {
      isConfigModalVisible.value = !isConfigModalVisible.value;
    };

    function getCookie(name) {
      let cookieValue = null;
      if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
          const cookie = cookies[i].trim();
          if (cookie.substring(0, name.length + 1) === name + "=") {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
            break;
          }
        }
      }
      return cookieValue;
    }

    watch(
      currentConfigValues,
      (newValues) => {
        // Handling new dynamic config values added via tags.
        if (!currentModel.value || !currentModel.value.configOptions) {
          return;
        }
        currentModel.value.configOptions.forEach((config) => {
          const configKey = config.key;
          const selectedValue = newValues[configKey];

          if (!selectedValue) {
            return;
          }

          // Duplicate check:
          const optionExists = config.options.some(
            (option) => option.value === selectedValue
          );

          // New Tag:
          if (!optionExists) {
            config.options.push({ value: selectedValue, text: selectedValue });
          }
        });
      },
      // NOTE: not working without deep: true.
      { deep: true }
    );

    return {
      isSidebarOpen,
      hamburgerVisible,
      newMessage,
      chatMessagesContainer,
      chatModels,
      currentModel,
      messages,
      toggleSidebar,
      selectModel,
      sendMessage,
      handleCategoryClick,
      isCategoryActive,
      currentConfigValues,
      isConfigModalVisible,
      toggleConfigModal,
    };
  },
});
app.component("vue-single-select", VueSingleSelect);
app.mount("#app");
