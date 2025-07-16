const VueSingleSelect = {
  template: '<select ref="selectEl" style="width: 100%;"></select>',
  props: {
    modelValue: [String, Array],
    options: { type: Array, default: () => [] },
  },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    const selectEl = ref(null);

    onMounted(() => {
      const el = $(selectEl.value);
      el.select2({
        dropdownParent: el.closest('.modal-content'),
        data: props.options.map((opt) => ({ id: opt.value, text: opt.text })),
        tags: true,
        createTag: (params) => ({ id: params.term, text: params.term, newTag: true }),
      })
        .val(props.modelValue)
        .trigger("change")
        .on("change", function () {
          emit("update:modelValue", $(this).val());
        });
    });

    watch(
      () => props.modelValue,
      (newValue) => {
        $(selectEl.value).val(newValue).trigger("change.select2");
      }
    );

    watch(
      () => props.options,
      (newOptions) => {
        const el = $(selectEl.value);
        // clear and re-initialize
        el.empty();
        el.select2({
          dropdownParent: el.closest('.modal-content'),
          data: newOptions.map((opt) => ({ id: opt.value, text: opt.text })),
          tags: true,
          createTag: (params) => ({ id: params.term, text: params.term, newTag: true }),
        });
        el.val(props.modelValue).trigger("change");
      }
    );

    onUnmounted(() => {
      $(selectEl.value).select2("destroy");
    });

    return { selectEl };
  },
};
