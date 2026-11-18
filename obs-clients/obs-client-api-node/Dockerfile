# Install the application dependencies in a full UBI Node docker image
FROM registry.access.redhat.com/ubi9/nodejs-24:9.9-1794494359@sha256:d843698c5564f9a066a9f45bb1b0392b0b0926f3aa1b37a242b99ed19f16408a

# Copy the manifest and the lockfile: the image gets exactly the audited dependency tree
COPY package.json package-lock.json ./

# Install app dependencies (clean, reproducible install from the lockfile)
RUN npm ci --omit=dev

# Copy the dependencies into a minimal Node.js image
FROM registry.access.redhat.com/ubi9/nodejs-24-minimal:9.9-1794493509@sha256:ea0ea1db6a8cce73129156de5153bd34e2d176162e7511343b3136d6f7e2a318

# Install app dependencies
COPY --from=0 /opt/app-root/src/node_modules /opt/app-root/src/node_modules
COPY ./app/ /opt/app-root/src/app
COPY package.json /opt/app-root/src/

RUN ls -l /opt/app-root/src/

ENV NODE_ENV production
ENV PORT 8080
EXPOSE 8080
CMD ["npm", "start"]