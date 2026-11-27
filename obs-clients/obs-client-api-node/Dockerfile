# Install the application dependencies in a full UBI Node docker image
FROM registry.access.redhat.com/ubi9/nodejs-24:1795496937@sha256:0067c15398ece743e462637c8581b1b31027a7a2d3112e610ad700bde3b03f1b

# Copy the manifest and the lockfile: the image gets exactly the audited dependency tree
COPY package.json package-lock.json ./

# Install app dependencies (clean, reproducible install from the lockfile)
RUN npm ci --omit=dev

# Copy the dependencies into a minimal Node.js image
FROM registry.access.redhat.com/ubi9/nodejs-24-minimal:1795226993@sha256:b28ac707c01bc8c9a1cbaacc26b8f1589ae1d16fe4927e502928cbb36f7271e0

# Install app dependencies
COPY --from=0 /opt/app-root/src/node_modules /opt/app-root/src/node_modules
COPY ./app/ /opt/app-root/src/app
COPY package.json /opt/app-root/src/

RUN ls -l /opt/app-root/src/

ENV NODE_ENV production
ENV PORT 8080
EXPOSE 8080
CMD ["npm", "start"]