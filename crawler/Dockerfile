FROM mcr.microsoft.com/playwright:v1.58.2-jammy

WORKDIR /app

COPY package*.json ./
RUN npm install

RUN mkdir -p output

COPY . .

CMD ["npm", "start"]
