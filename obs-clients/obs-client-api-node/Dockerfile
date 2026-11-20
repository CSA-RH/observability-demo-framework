# Install the application dependencies in a full UBI Node docker image
FROM registry.access.redhat.com/ubi9/nodejs-24:1795040207@sha256:5788fc5170268cf54cde8f781e9aa98068e6c996dec2b48882bf4086e7c95f92

# Copy the manifest and the lockfile: the image gets exactly the audited dependency tree
COPY package.json package-lock.json ./

# Install app dependencies (clean, reproducible install from the lockfile)
RUN npm ci --omit=dev

# Copy the dependencies into a minimal Node.js image
FROM registry.access.redhat.com/ubi9/nodejs-24-minimal:1795041330@sha256:94e1482b6fe50b5a99692d4cea62309b54201f405d12766f2ebe37ab49692f29

# Install app dependencies
COPY --from=0 /opt/app-root/src/node_modules /opt/app-root/src/node_modules
COPY ./app/ /opt/app-root/src/app
COPY package.json /opt/app-root/src/

RUN ls -l /opt/app-root/src/

ENV NODE_ENV production
ENV PORT 8080
EXPOSE 8080
CMD ["npm", "start"]