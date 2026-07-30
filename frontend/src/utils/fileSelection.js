export const getSelectedFileQueue = (files, selectedIds) => (
  files.filter((file) => selectedIds.has(file.id))
);

export const clearSelectedConversionResults = (results, selectedIds) => {
  const nextResults = { ...results };
  selectedIds.forEach((id) => delete nextResults[id]);
  return nextResults;
};
