import axios from "axios";

export const api = axios.create({ baseURL: "/api" });

// ── Types ─────────────────────────────────────────────────────────────────────

export interface CardOut {
  id: number;
  game: string;
  name: string;
  set_id: string;
  set_name: string;
  card_number: string;
  image_url: string | null;
  tcgplayer_product_id: number | null;
}

export interface SetOut {
  set_id: string;
  set_name: string;
  game: string;
  card_count: number;
}

export interface InventoryItemOut {
  id: number;
  card: CardOut;
  condition: string;
  quantity: number;
  tcgplayer_price: string | null;
  ebay_price: string | null;
  tcgplayer_sku_id: number | null;
  ebay_inventory_sku: string | null;
  ebay_offer_id: string | null;
  listed_on_tcgplayer: boolean;
  listed_on_ebay: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrderOut {
  id: number;
  platform: string;
  external_order_id: string;
  inventory_item_id: number | null;
  quantity_sold: number;
  sale_price: string | null;
  sold_at: string | null;
  synced_at: string;
}

// ── API calls ─────────────────────────────────────────────────────────────────

export const getSets = (game: string) =>
  api.get<SetOut[]>("/cards/sets", { params: { game } }).then((r) => r.data);

export const getCardsBySet = (game: string, set_id: string) =>
  api.get<CardOut[]>("/cards/by-set", { params: { game, set_id } }).then((r) => r.data);

export const getInventory = () =>
  api.get<InventoryItemOut[]>("/inventory").then((r) => r.data);

export const createInventoryItem = (data: {
  card_id: number;
  condition: string;
  quantity: number;
  tcgplayer_price: string | null;
  ebay_price: string | null;
  notes: string | null;
}) => api.post<InventoryItemOut>("/inventory", data).then((r) => r.data);

export const updateInventoryItem = (id: number, data: Partial<InventoryItemOut>) =>
  api.patch<InventoryItemOut>(`/inventory/${id}`, data).then((r) => r.data);

export const deleteInventoryItem = (id: number) =>
  api.delete(`/inventory/${id}`);

export const importTCGPlayerCSV = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return api
    .post<{ created: number; updated: number; skipped: number }>(
      "/inventory/import/tcgplayer-csv",
      form,
      { headers: { "Content-Type": "multipart/form-data" } }
    )
    .then((r) => r.data);
};

export const listOnTCGPlayer = (id: number) =>
  api.post(`/tcgplayer/list/${id}`).then((r) => r.data);

export const delistFromTCGPlayer = (id: number) =>
  api.post(`/tcgplayer/delist/${id}`).then((r) => r.data);

export const listOnEbay = (id: number) =>
  api.post(`/ebay/list/${id}`).then((r) => r.data);

export const delistFromEbay = (id: number) =>
  api.post(`/ebay/delist/${id}`).then((r) => r.data);

export const getOrders = () =>
  api.get<OrderOut[]>("/orders").then((r) => r.data);

export const getSettings = () =>
  api.get<Record<string, unknown>>("/settings").then((r) => r.data);

export const getEbayAuthUrl = () =>
  api.get<{ auth_url: string }>("/ebay/auth-url").then((r) => r.data);

export const getEbayStatus = () =>
  api.get<{ authenticated: boolean }>("/ebay/status").then((r) => r.data);

export const syncTCGPlayerOrders = () =>
  api.post("/tcgplayer/orders/sync").then((r) => r.data);

export const syncEbayOrders = () =>
  api.post("/ebay/orders/sync").then((r) => r.data);
