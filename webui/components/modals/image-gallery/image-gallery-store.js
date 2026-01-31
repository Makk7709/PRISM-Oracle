import { createStore } from "/js/AlpineStore.js";
import { fetchApi } from "/js/api.js";

/**
 * Image Gallery Store
 * Gallery for viewing and managing generated images
 */
const model = {
  // State
  isLoading: false,
  isDeleting: false,
  images: [],
  error: null,
  selectedImage: null,
  confirmDelete: null, // Image pending deletion confirmation
  
  // Lifecycle
  init() {
    // Nothing to initialize
  },

  // Open the gallery modal
  async open() {
    if (this.isLoading) return;
    
    this.isLoading = true;
    this.error = null;
    this.images = [];
    this.selectedImage = null;

    try {
      // Open modal first for immediate feedback
      const closePromise = window.openModal("modals/image-gallery/image-gallery.html");
      
      // Fetch images
      await this.fetchImages();
      
      // Wait for modal close
      await closePromise;
      this.destroy();
      
    } catch (error) {
      console.error("Image gallery error:", error);
      this.error = error?.message || "Failed to load images";
      this.isLoading = false;
    }
  },

  // Fetch images from the generated_images folder
  async fetchImages() {
    try {
      const response = await fetchApi(
        `/get_work_dir_files?path=${encodeURIComponent("tmp/generated_images")}`
      );

      if (!response.ok) {
        this.error = "Impossible de charger les images";
        this.images = [];
        return;
      }
      
      const jsonData = await response.json();
      const entries = jsonData?.data?.entries || [];
      
      // Filter only image files and sort by date (newest first)
      const imageExtensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp'];
      
      this.images = entries
        .filter(entry => {
          if (entry.is_dir) return false;
          const ext = entry.name.toLowerCase().slice(entry.name.lastIndexOf('.'));
          return imageExtensions.includes(ext);
        })
        .sort((a, b) => {
          // Sort by modification time, newest first
          const dateA = new Date(a.modified || 0);
          const dateB = new Date(b.modified || 0);
          return dateB - dateA;
        })
        .map(entry => ({
          name: entry.name,
          path: `tmp/generated_images/${entry.name}`,
          url: `/image_get?path=tmp/generated_images/${entry.name}`,
          size: entry.size,
          date: entry.modified ? new Date(entry.modified) : null
        }));
        
    } catch (error) {
      console.error("Error fetching images:", error);
      this.error = "Impossible de charger les images";
      this.images = [];
    } finally {
      this.isLoading = false;
    }
  },

  // Select an image for preview
  selectImage(image) {
    this.selectedImage = image;
  },

  // Close preview
  closePreview() {
    this.selectedImage = null;
  },

  // Download image
  downloadImage(image) {
    const link = document.createElement('a');
    link.href = image.url;
    link.download = image.name;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  },

  // Show delete confirmation
  showDeleteConfirm(image, event) {
    if (event) {
      event.stopPropagation(); // Prevent opening preview
    }
    this.confirmDelete = image;
  },

  // Cancel delete
  cancelDelete() {
    this.confirmDelete = null;
  },

  // Delete image
  async deleteImage(image) {
    if (!image) return;
    
    this.isDeleting = true;
    this.error = null;
    
    try {
      const response = await fetchApi("/delete_work_dir_file", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          path: image.path,
          currentPath: "tmp/generated_images"
        })
      });

      if (!response.ok) {
        throw new Error("Impossible de supprimer l'image");
      }

      // Remove from local list
      this.images = this.images.filter(img => img.name !== image.name);
      
      // Close preview if deleting the selected image
      if (this.selectedImage?.name === image.name) {
        this.selectedImage = null;
      }
      
      this.confirmDelete = null;
      
    } catch (error) {
      console.error("Error deleting image:", error);
      this.error = "Impossible de supprimer l'image";
    } finally {
      this.isDeleting = false;
    }
  },

  // Format file size
  formatSize(bytes) {
    if (!bytes) return '';
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    return `${size.toFixed(1)} ${units[unitIndex]}`;
  },

  // Format date
  formatDate(date) {
    if (!date) return '';
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  },

  // Close modal
  handleClose() {
    window.closeModal();
  },

  // Cleanup
  destroy() {
    this.isLoading = false;
    this.isDeleting = false;
    this.images = [];
    this.error = null;
    this.selectedImage = null;
    this.confirmDelete = null;
  }
};

export const store = createStore("imageGallery", model);
