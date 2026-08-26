<!-- capsule-v2 -->
# metadata-driven-entity-schema

## Source
- Repo: `twenty-crm`
- Path: `packages/twenty-server/src/engine/metadata-modules/object-metadata/object-metadata.entity.ts`
- Symbol: `ObjectMetadataEntity` (+ companion `FieldMetadataEntity` under `metadata-modules/field-metadata/`)
- Lines: 33-46 (class + workspace-scoped unique indexes), 47-115 (columns incl. upgrade-gated fields)
- Commit: `a6eedd8bf2afad74b6c9a68c9ccaa06d3ce753a0`
- Graph Node: `ext-twenty-crm.packages.twenty-server.src.engine.metadata-modules.object-metadata.object-metadata.entity.ObjectMetadataEntity`

## Signature & Data Shape
```typescript
@Entity('objectMetadata')
@Unique('IDX_OBJECT_METADATA_NAME_SINGULAR_WORKSPACE_ID_UNIQUE', ['nameSingular', 'workspaceId'])
@Unique('IDX_OBJECT_METADATA_NAME_PLURAL_WORKSPACE_ID_UNIQUE', ['namePlural', 'workspaceId'])
export class ObjectMetadataEntity extends SyncableEntity {
  @PrimaryGeneratedColumn('uuid') id: string;
  @Column({ nullable: true, type: 'uuid' }) dataSourceId: string;  // @deprecated FK dropped, column kept
  @Column({ nullable: false }) nameSingular: string;
  @Column({ nullable: false }) namePlural: string;
  @Column({ nullable: false }) labelSingular: string;
  @Column({ nullable: false }) labelPlural: string;
  // ... isCustom / isActive / isSystem / labelIdentifierFieldId / imageIdentifierFieldId ...
  @WasIntroducedInUpgrade({ upgradeCommandName: ADD_OBJECT_METADATA_OPEN_RECORD_IN_UPGRADE_COMMAND_NAME })
  @Column({ type: 'enum', enum: Object.values(ObjectOpenRecordIn), default: ObjectOpenRecordIn.USER_CHOICE })
  openRecordIn: ObjectOpenRecordIn;
  // ... metaWritable via ADD_METADATA_WRITABILITY_UPGRADE_COMMAND_NAME (2.32) ...
}
```

## Decisive Source Excerpt
```typescript
@Unique('IDX_OBJECT_METADATA_NAME_SINGULAR_WORKSPACE_ID_UNIQUE', [
  'nameSingular',
  'workspaceId',
])
@Unique('IDX_OBJECT_METADATA_NAME_PLURAL_WORKSPACE_ID_UNIQUE', [
  'namePlural',
  'workspaceId',
])
export class ObjectMetadataEntity
  extends SyncableEntity
  implements Required<ObjectMetadataEntity>
{
  @PrimaryGeneratedColumn('uuid')
  id: string;

  // @deprecated - FK dropped, column kept for data preservation only
  @Column({ nullable: true, type: 'uuid' })
  dataSourceId: string;
```

## Flow
1. Tenant objects/fields are ROWS in metadata catalogs (`objectMetadata`/`fieldMetadata` tables), never hardcoded classes; runtime ORM entities and GraphQL schemas are COMPILED from these rows per workspace.
2. Uniqueness is per-workspace composite (`nameSingular+workspaceId`, `namePlural+workspaceId`) — the same object name may exist in every tenant.
3. `isCustom: false + isSystem: true` marks standard core objects shipped by the product; `isCustom: true` marks tenant-defined objects created through settings/API.
4. Schema evolution of the METADATA ITSELF rides the upgrade system: new columns are stamped with `@WasIntroducedInUpgrade({upgradeCommandName})` / `@WasRemovedInUpgrade` constants naming the versioned command that adds/drops them — this is how the metadata schema participates in zero-downtime rolling upgrades (see upgrade-aware capsules).
5. Deprecated columns (`dataSourceId`) keep their physical column after FK removal purely for data preservation.

## Invariant
Tenant-defined schema lives as synchronized catalog rows with per-workspace composite uniqueness; the metadata catalog's own columns are versioned through explicit upgrade-command decorators so old code never selects a column that does not exist yet. Dropping an FK must NOT drop the column it preserved.

## Direct-Test Probe
No dedicated service/entity spec exists at HEAD (coverage caveat). Behavior pins live in neighboring utils specs:

```bash
grep -c "@Unique(" packages/twenty-server/src/engine/metadata-modules/object-metadata/object-metadata.entity.ts                            # => 2 (per-workspace composite legs)
grep -c "WasIntroducedInUpgrade" packages/twenty-server/src/engine/metadata-modules/object-metadata/object-metadata.entity.ts              # => 6 versioned-column stamps
grep -n "extends SyncableEntity" packages/twenty-server/src/engine/metadata-modules/object-metadata/object-metadata.entity.ts              # => :42
ls packages/twenty-server/src/engine/metadata-modules/field-metadata/field-metadata.entity.ts                                              # companion catalog entity
```

## Graph Query
```bash
echo '{"project":"ext-twenty-crm","name_pattern":"ObjectMetadataEntity"}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt the metadata-row-as-schema pattern with per-workspace composite uniqueness; adopt the `@WasIntroducedInUpgrade` column-versioning discipline only together with the upgrade-aware adapter plane.
