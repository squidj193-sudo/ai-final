FROM node:20-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 5173

# 啟用 --host 以允許從 Docker 外部存取 Vite 開發伺服器
CMD ["npm", "run", "dev", "--", "--host"]
