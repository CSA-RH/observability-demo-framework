# Stage 1: Build the React app using Red Hat UBI Node.js 20 image
FROM registry.access.redhat.com/ubi9/nodejs-20 AS build

# Set working directory
WORKDIR /app

# Use root user to copy files and set permissions
USER 0

# Copy package.json and package-lock.json (if available)
COPY package*.json ./

# Install dependencies
RUN npm install --omit=dev

# Copy the rest of the application source code
COPY . .

# Build the React app
RUN npm run build

# Set permissions for the /app directory
RUN chown -R 1001:0 /app

# Switch to the non-root user
USER 1001

# Stage 2: Serve the React app using UBI8 Nginx
FROM registry.access.redhat.com/ubi9/nginx-124

# Use non-root user
USER 1001

# Copy the built React app from the build stage
COPY --chown=1001:0 --from=build /app/dist /opt/app-root/src
COPY misc/react-app.conf /opt/app-root/etc/nginx.default.d/

# Expose port 8080 (default for UBI8 Nginx)
EXPOSE 8080

# Start the Nginx server
CMD ["nginx", "-g", "daemon off;"]