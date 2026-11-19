
import os
import re
import json
import asyncio
from pathlib import Path

import discord

TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])

DATA_FILE = Path("/app/data/roles_data.json")
DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
PATTERN = re.compile(r"^\s*rol(?:\s*-\s*|\s+)(.*?)\s*$", re.I)

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)
lock = asyncio.Lock()


def load_data():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return {}


def save_data(data):
    temporary = DATA_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False),
        encoding="utf-8"
    )
    temporary.replace(DATA_FILE)


@bot.event
async def on_ready():
    print(f"CATVICTUS ROLES conectado: {bot.user}")


@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    if message.channel.id != CHANNEL_ID:
        return

    match = PATTERN.fullmatch(message.content)
    if not match:
        return

    name = match.group(1).strip()

    if (
        not name
        or len(name) > 100
        or "\n" in name
        or "\r" in name
        or "@everyone" in name.lower()
        or "@here" in name.lower()
    ):
        await message.reply(
            "❌ Nombre no válido. Revisa tu nombre de COD Mobile.",
            mention_author=False
        )
        return

    async with lock:
        guild = message.guild
        member = message.author
        data = load_data()
        guild_key = str(guild.id)
        records = data.setdefault(guild_key, {})
        member_key = str(member.id)

        try:
            old_role_id = records.get(member_key)
            old_role = (
                guild.get_role(old_role_id)
                if old_role_id else None
            )

            if old_role and old_role.name == name:
                if old_role not in member.roles:
                    await member.add_roles(old_role)
                await message.reply(
                    "✅ Ya tienes asignado ese rol.",
                    mention_author=False
                )
                return

            # Nunca reutilizar roles ajenos al sistema.
            existing = discord.utils.get(guild.roles, name=name)
            if existing:
                await message.reply(
                    "⚠️ Ese nombre ya existe como rol. "
                    "Solicita ayuda al staff.",
                    mention_author=False
                )
                return

            # Los roles nuevos no tienen permisos especiales.
            new_role = await guild.create_role(
                name=name,
                permissions=discord.Permissions.none(),
                mentionable=False,
                hoist=False,
                reason="Rol COD Mobile solicitado"
            )

            try:
                await member.add_roles(
                    new_role,
                    reason="Solicitud de rol COD Mobile"
                )
            except discord.HTTPException:
                await new_role.delete()
                raise

            records[member_key] = new_role.id
            save_data(data)

            if old_role and old_role in member.roles:
                try:
                    await member.remove_roles(
                        old_role,
                        reason="Cambio de nombre COD Mobile"
                    )
                except discord.HTTPException:
                    pass

            await message.reply(
                "✅ Rol asignado: **"
                + discord.utils.escape_markdown(name)
                + "**",
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none()
            )

        except discord.Forbidden:
            await message.reply(
                "❌ El bot necesita permisos para gestionar roles.",
                mention_author=False
            )
        except discord.HTTPException:
            await message.reply(
                "❌ Ocurrió un error. Intenta nuevamente.",
                mention_author=False
            )


bot.run(TOKEN)
